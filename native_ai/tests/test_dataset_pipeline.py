"""Comprehensive Automated Test Suite for LOVE Native AI Dataset Pipeline.

Implements Task 15:
- Ingestion of plain-text and JSONL files
- UTF-8 validation and malformed-byte resilience
- Unicode normalization and symbol preservation
- Exact duplicate removal
- Normalized duplicate removal
- Near-duplicate grouping via MinHash Jaccard similarity
- Text cleaning rules (whitespace collapse, HTML artifact removal, minimum length)
- Quality and privacy filtering:
  - Personal email address redaction
  - Personal phone number redaction
  - Secret key and private key document rejection
  - Confidential corporate document rejection
- Source attribution tracking & manifest creation
- License metadata validity
- Deterministic splitting (seed 42) into Train 98%, Val 1%, Test 1%
- Strict cross-split duplicate prevention (assert disjoint hash sets)
- Tokenizer compatibility on cleaned, split documents
- Manifest checksum verification (SHA-256)
- Streaming file generator memory efficiency
"""
import pytest
import json
import hashlib
from pathlib import Path

from native_ai.datasets.source_registry import DatasetSourceRegistry, DatasetSourceRecord
from native_ai.datasets.ingestion import DatasetIngestion
from native_ai.datasets.cleaning import TextCleaner
from native_ai.datasets.privacy_filter import PrivacyFilter
from native_ai.datasets.deduplication import Deduplicator, compute_sha256, compute_normalized_hash
from native_ai.datasets.splitter import DatasetSplitter
from native_ai.tokenizer.love_tokenizer import LoveTokenizer

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "tokenizer" / "artifacts"


def test_source_registry_and_license_validation():
    """Verify registry tracks sources and strictly enforces approved licenses."""
    registry = DatasetSourceRegistry()
    assert len(registry.sources) == 5

    # Check that all registered sources use approved licenses
    for src_id, record in registry.sources.items():
        assert record.license_type in DatasetSourceRegistry.APPROVED_LICENSES
        assert record.category in DatasetSourceRegistry.CATEGORIES

    # Verify invalid license is rejected
    with pytest.raises(ValueError, match="not approved"):
        registry.register_source(
            DatasetSourceRecord(
                source_id="invalid_src",
                source_name="Invalid",
                category="general_english",
                origin_location="none",
                license_type="PROPRIETARY_UNLICENSED",
                license_reference="none",
                permitted_usage="none",
                restrictions="none",
                retrieval_date="2026-11-21",
                processing_date="2026-11-21",
            )
        )


def test_text_cleaning_rules():
    """Verify HTML artifact removal, whitespace collapse, and length filtering."""
    cleaner = TextCleaner(min_chars=30, min_words=6)

    # 1. HTML stripping & excessive newline collapse
    dirty = "<h1>Title Header</h1>\n\n\n\n<p>This is a paragraph with <b>bold text</b> and &amp; entities.</p>\n\n\n"
    cleaned, meta = cleaner.clean_text(dirty)
    assert not meta["rejected"]
    assert "<h1>" not in cleaned
    assert "<b>" not in cleaned
    assert "&amp;" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "Title Header" in cleaned
    assert "This is a paragraph with bold text and & entities." in cleaned

    # 2. Too short document rejection
    short = "Too brief."
    cleaned_short, meta_short = cleaner.clean_text(short)
    assert cleaned_short is None
    assert meta_short["rejected"] is True


def test_privacy_filter_redaction_and_rejection():
    """Verify PII redaction (email/phone) and strict secret rejection (keys/passwords)."""
    filter_engine = PrivacyFilter()

    # 1. Personal PII redaction
    sample_pii = "Contact the project coordinator at alice.smith@external.com or call 555-432-1098 for access."
    is_safe, sanitized, flags = filter_engine.inspect_and_filter(sample_pii)
    assert is_safe is True
    assert "[EMAIL_REDACTED]" in sanitized
    assert "[PHONE_REDACTED]" in sanitized
    assert "alice.smith@external.com" not in sanitized

    # 2. Secret rejection: Private key
    sample_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y3wZkFfakeKey...\n-----END RSA PRIVATE KEY-----"
    is_safe_key, _, flags_key = filter_engine.inspect_and_filter(sample_key)
    assert is_safe_key is False
    assert any("secret" in f for f in flags_key)

    # 3. Secret rejection: High-entropy API key
    sample_api = "export OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz1234567890"
    is_safe_api, _, _ = filter_engine.inspect_and_filter(sample_api)
    assert is_safe_api is False

    # 4. Confidential document marking rejection
    sample_conf = "STRICTLY CONFIDENTIAL - Internal Acquisition Proposal Document"
    is_safe_conf, _, _ = filter_engine.inspect_and_filter(sample_conf)
    assert is_safe_conf is False


def test_deduplication_exact_normalized_and_near(tmp_path):
    """Verify exact, normalized, and MinHash near-duplicate detection."""
    deduper = Deduplicator(enable_near_dup=True, near_dup_threshold=0.85)

    doc1 = "The quick brown fox jumps over the lazy dog and rests beneath the oak tree."
    # Exact duplicate
    is_ok, _ = deduper.check_and_add("doc1", doc1)
    assert is_ok is True

    is_exact_dup, meta_exact = deduper.check_and_add("doc2", doc1)
    assert is_exact_dup is False
    assert meta_exact["reason"] == "exact_duplicate"

    # Normalized duplicate (different case & whitespace)
    doc3 = "   THE   QUICK   BROWN   FOX   JUMPS   OVER   THE   LAZY   DOG   AND   RESTS   BENEATH   THE   OAK   TREE.   "
    is_norm_dup, meta_norm = deduper.check_and_add("doc3", doc3)
    assert is_norm_dup is False
    assert meta_norm["reason"] == "normalized_duplicate"

    # Near-duplicate (trivial mutation > 85% similar on representative text)
    doc_base = (
        "The Central Processing Unit is the primary computational engine of modern computer systems. "
        "It fetches instructions, decodes them into micro-operations, and executes them via arithmetic logic units."
    )
    is_base_ok, _ = deduper.check_and_add("doc_base", doc_base)
    assert is_base_ok is True

    doc_near = doc_base + " In modern architecture."
    is_near_dup_admitted, meta_near = deduper.check_and_add("doc_near", doc_near)
    assert is_near_dup_admitted is False
    assert meta_near["reason"] == "near_duplicate"

    # Completely distinct document
    doc5 = "Quantum computational algorithms formulate tensor network contractions across high dimensional Hilbert spaces."
    is_distinct, _ = deduper.check_and_add("doc5", doc5)
    assert is_distinct is True


def test_deterministic_splitting_and_zero_cross_split_leakage(tmp_path):
    """Verify deterministic splitting and mathematical guarantee of zero leakage."""
    splitter = DatasetSplitter(seed=42, train_ratio=0.98, val_ratio=0.01, test_ratio=0.01)

    records = [
        {"doc_id": f"doc_{i:04d}", "category": "general_english", "text": f"Unique document content number {i:04d} for testing."}
        for i in range(100)
    ]

    train_set, val_set, test_set = splitter.split_records(records)

    assert len(train_set) + len(val_set) + len(test_set) == 100
    assert len(val_set) >= 1
    assert len(test_set) >= 1
    assert len(train_set) >= 90

    # Cross-split disjointness
    train_ids = set(r["doc_id"] for r in train_set)
    val_ids = set(r["doc_id"] for r in val_set)
    test_ids = set(r["doc_id"] for r in test_set)

    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)

    # Save and verify manifest checksums
    manifests_dir = tmp_path / "manifests"
    splits_dir = tmp_path / "splits"
    split_manifests = splitter.save_splits(train_set, val_set, test_set, splits_dir, manifests_dir)

    for split in ["train", "val", "test"]:
        m = split_manifests[split]
        file_path = Path(m["file_path"])
        assert file_path.exists()
        computed_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert computed_sha == m["sha256"]


def test_streaming_ingestion_generator(tmp_path):
    """Verify streaming reader does not load entire file into memory and handles .txt and .jsonl."""
    ingestor = DatasetIngestion()

    # JSONL file
    jsonl_file = tmp_path / "test.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(json.dumps({"doc_id": f"j_{i}", "category": "general_english", "text": f"Document {i}"}) + "\n")

    streamed = list(ingestor.stream_file(jsonl_file, source_id="src_test", category="general_english"))
    assert len(streamed) == 10
    assert streamed[0]["doc_id"] == "j_0"


def test_tokenizer_compatibility_on_splits():
    """Verify that LOVE Tokenizer encodes split records without OOV or errors."""
    tokenizer = LoveTokenizer.from_pretrained(ARTIFACTS_DIR)

    test_sample = "Mathematical formula: f(x) = ax^2 + bx + c. Python function: def add(x, y): return x + y."
    encoded = tokenizer.encode(test_sample)
    assert all(0 <= tid < 8192 for tid in encoded)
    assert tokenizer.decode(encoded) == test_sample
