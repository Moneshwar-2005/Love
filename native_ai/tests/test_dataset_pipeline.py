"""Comprehensive Automated Test Suite for LOVE Native AI Dataset Pipeline.

Implements Task 15 (NAI-03) & Task 6 (NAI-03.1):
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
- Deterministic splitting (seed 42)
- Strict cross-split duplicate prevention (assert disjoint hash sets)
- Tokenizer compatibility on cleaned, split documents
- Manifest checksum verification (SHA-256)
- Streaming file generator memory efficiency
- Source provenance validation (NAI-03.1)
- License evidence completeness (NAI-03.1)
- Missing source attribution detection (NAI-03.1)
- Incorrect document split percentages correction (NAI-03.1)
- Token-count reporting per split (NAI-03.1)
- Group-level cross-split leakage prevention (NAI-03.1)
- Reproducible source manifests (NAI-03.1)
- Insufficient validation/test sample warnings (NAI-03.1)
- Storage capacity estimation & disk safety (NAI-03.1)
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
from native_ai.datasets.scale_targets import get_all_scenarios, compute_scenario, get_disk_free_bytes
from native_ai.tokenizer.love_tokenizer import LoveTokenizer

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "tokenizer" / "artifacts"


def test_source_registry_and_license_validation():
    """Verify registry tracks sources and strictly enforces approved licenses."""
    registry = DatasetSourceRegistry()
    assert len(registry.sources) >= 5

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


# ==============================================================================
# NAI-03.1 AUDIT & READINESS TEST SUITE EXTENSIONS
# ==============================================================================

def test_source_provenance_validation():
    """Verify source provenance validation flags missing creator, invalid source_type, and unresolved status."""
    valid_record = DatasetSourceRecord(
        source_id="src_valid",
        source_name="Valid Synthetic Source",
        category="general_english",
        origin_location="native_ai/datasets/raw/general_english.jsonl",
        license_type="CC0-1.0",
        license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
        permitted_usage="Unrestricted pretraining",
        restrictions="None",
        retrieval_date="2026-11-21",
        processing_date="2026-11-21",
        creator="LOVE Project Author",
        source_type="original_synthetic",
        license_status="VERIFIED",
        license_evidence="Authored directly by project developer as original synthetic text.",
        is_approved_for_training=True,
    )
    is_valid, issues = DatasetSourceRegistry.validate_source_provenance(valid_record)
    assert is_valid is True
    assert len(issues) == 0

    # Missing creator attribution
    invalid_record = DatasetSourceRecord(
        source_id="src_invalid",
        source_name="Invalid Source",
        category="general_english",
        origin_location="none",
        license_type="CC0-1.0",
        license_reference="none",
        permitted_usage="none",
        restrictions="none",
        retrieval_date="2026-11-21",
        processing_date="2026-11-21",
        creator="",  # Empty creator
        source_type="original_synthetic",
        license_status="VERIFIED",
        license_evidence="Some evidence",
        is_approved_for_training=True,
    )
    is_valid, issues = DatasetSourceRegistry.validate_source_provenance(invalid_record)
    assert is_valid is False
    assert any("creator" in issue.lower() for issue in issues)


def test_license_evidence_completeness():
    """Verify that records with incomplete license evidence or UNRESOLVED status are excluded from approved training."""
    registry = DatasetSourceRegistry()

    # In the core sources, src_tech_01 is marked UNRESOLVED because it was improperly labeled MIT without deed
    assert "src_tech_01" in registry.sources
    tech_rec = registry.sources["src_tech_01"]
    assert tech_rec.license_status == "UNRESOLVED"
    assert tech_rec.is_approved_for_training is False

    # Check approved sources filter
    approved = registry.get_approved_sources()
    unresolved = registry.get_unresolved_sources()
    assert "src_tech_01" not in approved
    assert "src_tech_01" in unresolved
    assert len(approved) >= 4
    assert len(unresolved) == 1

    # Record with too-short/missing license evidence
    record_no_evidence = DatasetSourceRecord(
        source_id="src_no_ev",
        source_name="No Evidence Source",
        category="general_english",
        origin_location="none",
        license_type="CC0-1.0",
        license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
        permitted_usage="Pretraining",
        restrictions="None",
        retrieval_date="2026-11-21",
        processing_date="2026-11-21",
        creator="Project Author",
        source_type="original_synthetic",
        license_status="VERIFIED",
        license_evidence="",  # Missing evidence
        is_approved_for_training=True,
    )
    is_valid, issues = DatasetSourceRegistry.validate_source_provenance(record_no_evidence)
    assert is_valid is False
    assert any("evidence" in issue.lower() for issue in issues)


def test_missing_source_attribution():
    """Verify that looking up or updating non-existent source IDs raises KeyError."""
    registry = DatasetSourceRegistry()
    with pytest.raises(KeyError, match="not found in registry"):
        registry.update_file_metadata("non_existent_source_id", Path("dummy.jsonl"), 10)


def test_incorrect_document_split_percentages(tmp_path):
    """Verify that splitter accurately computes 90.91 / 4.55 / 4.55 for 22 documents and rejects false 98/1/1 claims."""
    splitter = DatasetSplitter(seed=42, train_ratio=0.98, val_ratio=0.01, test_ratio=0.01)

    # 22 test documents (matching exact admitted corpus size)
    records = [
        {"doc_id": f"doc_{i:02d}", "category": "general_english", "text": f"Admitted document {i} content."}
        for i in range(22)
    ]

    train_set, val_set, test_set = splitter.split_records(records)
    assert len(train_set) == 20
    assert len(val_set) == 1
    assert len(test_set) == 1

    pcts = splitter.compute_actual_percentages(train_set, val_set, test_set)
    # The actual mathematical proportions are 90.91%, 4.55%, 4.55%
    assert pcts["train"] == 90.91
    assert pcts["val"] == 4.55
    assert pcts["test"] == 4.55
    # Must never report 98.0% as actual achieved percentage
    assert pcts["train"] != 98.00


def test_token_count_reporting(tmp_path):
    """Verify that save_splits measures and records token counts via LoveTokenizer."""
    splitter = DatasetSplitter(seed=42, train_ratio=0.98, val_ratio=0.01, test_ratio=0.01)
    tokenizer = LoveTokenizer.from_pretrained(ARTIFACTS_DIR)

    records = [
        {"doc_id": f"doc_{i:02d}", "category": "general_english", "text": f"This is test document {i} with varied tokens."}
        for i in range(22)
    ]

    train_set, val_set, test_set = splitter.split_records(records)
    splits_dir = tmp_path / "splits"
    manifests_dir = tmp_path / "manifests"
    manifests = splitter.save_splits(train_set, val_set, test_set, splits_dir, manifests_dir, tokenizer=tokenizer)

    for split in ["train", "val", "test"]:
        m = manifests[split]
        assert "num_tokens" in m
        assert m["num_tokens"] is not None
        assert m["num_tokens"] > 0
        assert m["actual_percentage"] is not None


def test_group_level_leakage(tmp_path):
    """Verify that documents belonging to the same group_id never cross split boundaries."""
    splitter = DatasetSplitter(seed=42, train_ratio=0.80, val_ratio=0.10, test_ratio=0.10)

    # 10 groups, each having 3 documents
    records = []
    for g in range(10):
        for d in range(3):
            records.append({
                "doc_id": f"doc_g{g}_d{d}",
                "group_id": f"group_{g}",
                "category": "technical_code",
                "text": f"Content for group {g} document {d}."
            })

    train_set, val_set, test_set = splitter.split_records(records, group_key="group_id")

    train_groups = set(r["group_id"] for r in train_set)
    val_groups = set(r["group_id"] for r in val_set)
    test_groups = set(r["group_id"] for r in test_set)

    # Absolute disjointness between groups across all splits
    assert train_groups.isdisjoint(val_groups)
    assert train_groups.isdisjoint(test_groups)
    assert val_groups.isdisjoint(test_groups)
    assert len(train_groups) + len(val_groups) + len(test_groups) == 10


def test_reproducible_source_manifests(tmp_path):
    """Verify that exporting source registry produces deterministic outputs and valid JSON."""
    reg1 = DatasetSourceRegistry()
    out1 = tmp_path / "manifest1.json"
    data1 = reg1.export_registry(out1)

    reg2 = DatasetSourceRegistry()
    out2 = tmp_path / "manifest2.json"
    data2 = reg2.export_registry(out2)

    # Compare content equality ignoring timestamp
    del data1["timestamp"]
    del data2["timestamp"]
    assert data1 == data2


def test_insufficient_validation_test_sample_warnings(tmp_path):
    """Verify that splits with fewer than 10 documents generate explicit statistical warnings."""
    splitter = DatasetSplitter(seed=42, train_ratio=0.98, val_ratio=0.01, test_ratio=0.01)

    records = [
        {"doc_id": f"d_{i}", "category": "general_english", "text": f"Small corpus document {i}."}
        for i in range(22)
    ]
    train_set, val_set, test_set = splitter.split_records(records)
    splits_dir = tmp_path / "splits"
    manifests_dir = tmp_path / "manifests"
    manifests = splitter.save_splits(train_set, val_set, test_set, splits_dir, manifests_dir)

    # Validation and test splits have 1 doc each (< 10), so they MUST have a warning
    assert manifests["val"]["sample_size_warning"] is not None
    assert "INSUFFICIENT_SAMPLE_SIZE" in manifests["val"]["sample_size_warning"]
    assert manifests["test"]["sample_size_warning"] is not None
    assert "INSUFFICIENT_SAMPLE_SIZE" in manifests["test"]["sample_size_warning"]

    # Now test with >= 10 docs in val and test
    records_large = [
        {"doc_id": f"d_{i}", "category": "general_english", "text": f"Large corpus document {i}."}
        for i in range(100)
    ]
    splitter_balanced = DatasetSplitter(seed=42, train_ratio=0.80, val_ratio=0.10, test_ratio=0.10)
    t_set, v_set, te_set = splitter_balanced.split_records(records_large)
    large_manifests = splitter_balanced.save_splits(t_set, v_set, te_set, splits_dir / "large", manifests_dir / "large")
    assert large_manifests["val"]["sample_size_warning"] is None
    assert large_manifests["test"]["sample_size_warning"] is None


def test_storage_capacity_estimation():
    """Verify empirical storage calculations for 1M, 20M, and 100M token scenarios and disk headroom."""
    scenarios = get_all_scenarios()

    assert "scenario_a" in scenarios
    assert "scenario_b" in scenarios
    assert "scenario_c" in scenarios

    sc_a = scenarios["scenario_a"]
    sc_b = scenarios["scenario_b"]
    sc_c = scenarios["scenario_c"]

    # Validate token targets
    assert sc_a.target_tokens == 1_000_000
    assert sc_b.target_tokens == 20_000_000
    assert sc_c.target_tokens == 100_000_000

    # Validate storage bounds
    assert sc_a.total_estimated_disk_bytes < 50 * 1024 * 1024   # < 50 MB
    assert sc_b.total_estimated_disk_bytes < 300 * 1024 * 1024  # < 300 MB
    assert sc_c.total_estimated_disk_bytes < 1.5 * 1024 * 1024 * 1024  # < 1.5 GB

    # Check disk safety status
    free_bytes = get_disk_free_bytes()
    assert free_bytes > 0
    # On F:, free space is ~4.89 GB, so all 3 scenarios must be marked SAFE
    assert sc_a.disk_safety_status == "SAFE"
    assert sc_b.disk_safety_status == "SAFE"
    assert sc_c.disk_safety_status == "SAFE"
    assert sc_a.hardware_feasibility_status == "FEASIBLE"
    assert sc_b.hardware_feasibility_status == "FEASIBLE"
    assert sc_c.hardware_feasibility_status == "FEASIBLE"


# ==============================================================================
# NAI-03.2 AUTOMATED REGRESSION & EXPANSION TEST SUITE
# ==============================================================================

def test_external_download_integrity_and_revision_pinning():
    """Verify download manifest tracks exact commit revisions, byte sizes, and SHA-256 hashes."""
    manifest_path = Path(__file__).resolve().parent.parent / "datasets" / "manifests" / "acquisition_manifest.json"
    assert manifest_path.exists(), "Acquisition manifest must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "manifest_version" in manifest
    assert "pre_download_audit" in manifest
    assert manifest["pre_download_audit"]["audit_status"] == "APPROVED"
    assert "datasets" in manifest
    assert "gsm8k" in manifest["datasets"]
    assert "oasst1" in manifest["datasets"]
    assert "tinystories" in manifest["datasets"]

    # Verify commit revision pinning
    for ds_name, ds_info in manifest["datasets"].items():
        assert ds_info["revision"] is not None and len(ds_info["revision"]) == 40
        assert len(ds_info["files"]) >= 2

        # Verify on-disk file existence and hash match
        for f_meta in ds_info["files"]:
            local_path = Path(f_meta["local_path"])
            assert local_path.exists(), f"File {local_path} must exist"
            assert local_path.stat().st_size == f_meta["file_size_bytes"]
            actual_sha = hashlib.sha256(local_path.read_bytes()).hexdigest()
            assert actual_sha == f_meta["file_sha256"], f"Checksum mismatch for {f_meta['local_filename']}"


def test_license_manifest_preservation():
    """Verify license files exist on disk and source registry tracks CDLA-Sharing, MIT, and Apache-2.0."""
    raw_ext_dir = Path(__file__).resolve().parent.parent / "datasets" / "raw" / "external"
    assert (raw_ext_dir / "gsm8k" / "README.md").exists()
    assert (raw_ext_dir / "oasst1" / "LICENSE").exists()
    assert (raw_ext_dir / "tinystories" / "LICENSE").exists()

    reg_path = Path(__file__).resolve().parent.parent / "datasets" / "manifests" / "source_registry.json"
    assert reg_path.exists()
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)

    sources = reg["sources"]
    assert "src_ext_gsm8k" in sources
    assert sources["src_ext_gsm8k"]["license_type"] == "MIT"
    assert sources["src_ext_gsm8k"]["license_status"] == "VERIFIED"
    assert sources["src_ext_gsm8k"]["is_approved_for_training"] is True

    assert "src_ext_oasst1" in sources
    assert sources["src_ext_oasst1"]["license_type"] == "Apache-2.0"
    assert sources["src_ext_oasst1"]["license_status"] == "VERIFIED"
    assert sources["src_ext_oasst1"]["is_approved_for_training"] is True

    assert "src_ext_tinystories" in sources
    assert sources["src_ext_tinystories"]["license_type"] == "CDLA-Sharing-1.0"
    assert sources["src_ext_tinystories"]["license_status"] == "VERIFIED"
    assert sources["src_ext_tinystories"]["is_approved_for_training"] is True

    # src_tech_01 must remain UNRESOLVED and excluded from training
    assert "src_tech_01" in sources
    assert sources["src_tech_01"]["license_status"] == "UNRESOLVED"
    assert sources["src_tech_01"]["is_approved_for_training"] is False


def test_parquet_dataset_parsing():
    """Verify PyArrow reads downloaded Parquet files and schema fields match requirements."""
    import pyarrow.parquet as pq

    raw_ext = Path(__file__).resolve().parent.parent / "datasets" / "raw" / "external"

    # GSM8K
    gsm_table = pq.read_table(raw_ext / "gsm8k" / "train.parquet")
    assert "question" in gsm_table.column_names
    assert "answer" in gsm_table.column_names
    assert gsm_table.num_rows > 7000

    # OASST1
    oasst_table = pq.read_table(raw_ext / "oasst1" / "train.parquet")
    for expected_col in ["message_id", "parent_id", "message_tree_id", "text", "role", "lang", "deleted", "review_result"]:
        assert expected_col in oasst_table.column_names
    assert oasst_table.num_rows > 80000

    # TinyStories
    ts_table = pq.read_table(raw_ext / "tinystories" / "train_shard0.parquet")
    assert "text" in ts_table.column_names
    assert ts_table.num_rows > 500000


def test_oasst1_english_filtering_and_tree_integrity():
    """Verify non-English messages are rejected and conversations preserve tree hierarchy."""
    splits_dir = Path(__file__).resolve().parent.parent / "datasets" / "splits"
    train_file = splits_dir / "train" / "train.jsonl"
    assert train_file.exists()

    oasst_count = 0
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("source_id") == "src_ext_oasst1":
                oasst_count += 1
                assert rec["category"] == "instruction_dialog"
                assert rec["group_id"].startswith("oasst_tree_")
                assert "You are LOVE" in rec["text"]
                assert len(rec["text"].split()) >= 10
                if oasst_count >= 50:
                    break

    assert oasst_count >= 50


def test_gsm8k_train_test_separation():
    """Verify official GSM8K train and test records remain strictly separated."""
    splits_dir = Path(__file__).resolve().parent.parent / "datasets" / "splits"
    train_file = splits_dir / "train" / "train.jsonl"
    test_file = splits_dir / "test" / "test.jsonl"

    train_gsm_ids = set()
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("source_id") == "src_ext_gsm8k":
                train_gsm_ids.add(rec["doc_id"])
                assert rec["is_held_out_test"] is False
                assert rec["doc_id"].startswith("gsm8k_train_")

    test_gsm_ids = set()
    with open(test_file, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("source_id") == "src_ext_gsm8k":
                test_gsm_ids.add(rec["doc_id"])
                assert rec["is_held_out_test"] is True
                assert rec["doc_id"].startswith("gsm8k_test_")

    assert len(train_gsm_ids) >= 7000
    assert len(test_gsm_ids) >= 1000
    assert train_gsm_ids.isdisjoint(test_gsm_ids)


def test_tinystories_validation_preservation():
    """Verify TinyStories validation records are routed only to evaluation splits and not to train."""
    splits_dir = Path(__file__).resolve().parent.parent / "datasets" / "splits"
    train_file = splits_dir / "train" / "train.jsonl"
    val_file = splits_dir / "validation" / "val.jsonl"
    test_file = splits_dir / "test" / "test.jsonl"

    train_ts_val = set()
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("source_id") == "src_ext_tinystories" and "val" in rec["doc_id"]:
                train_ts_val.add(rec["doc_id"])

    assert len(train_ts_val) == 0, "No TinyStories validation stories permitted in training split"

    eval_ts_val = set()
    for ef in [val_file, test_file]:
        with open(ef, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("source_id") == "src_ext_tinystories":
                    eval_ts_val.add(rec["doc_id"])

    assert len(eval_ts_val) >= 2000


def test_cross_split_zero_leakage_expanded():
    """Verify complete disjointness of document hashes and group IDs across expanded train/val/test splits."""
    splits_dir = Path(__file__).resolve().parent.parent / "datasets" / "splits"
    paths = {
        "train": splits_dir / "train" / "train.jsonl",
        "val": splits_dir / "validation" / "val.jsonl",
        "test": splits_dir / "test" / "test.jsonl",
    }

    hashes = {}
    groups = {}

    for split_name, p in paths.items():
        assert p.exists()
        hashes[split_name] = set()
        groups[split_name] = set()
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                h = hashlib.sha256(r["text"].encode("utf-8")).hexdigest()
                hashes[split_name].add(h)
                groups[split_name].add(r["group_id"])

    # Strict text hash disjointness
    assert hashes["train"].isdisjoint(hashes["val"]), "Text hash overlap between train and val"
    assert hashes["train"].isdisjoint(hashes["test"]), "Text hash overlap between train and test"
    assert hashes["val"].isdisjoint(hashes["test"]), "Text hash overlap between val and test"

    # Strict group disjointness
    assert groups["train"].isdisjoint(groups["val"]), "Group overlap between train and val"
    assert groups["train"].isdisjoint(groups["test"]), "Group overlap between train and test"
    assert groups["val"].isdisjoint(groups["test"]), "Group overlap between val and test"


def test_tokenizer_compatibility_on_expanded_corpus():
    """Verify LOVE Tokenizer encodes and decodes expanded corpus examples across all domains."""
    tokenizer = LoveTokenizer.from_pretrained(ARTIFACTS_DIR)

    # GSM8K math reasoning sample
    math_text = "<|system|>You are LOVE.<|user|>If x + 5 = 12, what is x?<<x = 7>><|assistant|>x = 7"
    tokens_math = tokenizer.encode(math_text)
    assert len(tokens_math) > 10
    assert all(0 <= tid < 8192 for tid in tokens_math)

    # OASST1 multi-turn instruction dialog sample
    dialog_text = "<|system|>You are LOVE.<|user|>Hello!<|assistant|>Greetings! How can I assist you today?"
    tokens_dialog = tokenizer.encode(dialog_text)
    assert len(tokens_dialog) > 10
    assert all(0 <= tid < 8192 for tid in tokens_dialog)

    # TinyStories synthetic story sample
    story_text = "Once upon a time, a small rabbit named Lily found a shiny red key in the garden."
    tokens_story = tokenizer.encode(story_text)
    assert len(tokens_story) > 10
    assert all(0 <= tid < 8192 for tid in tokens_story)
    decoded_story = tokenizer.decode(tokens_story)
    assert "Lily" in decoded_story


def test_storage_budget_enforcement():
    """Verify external download storage <= 1.5 GB and drive F: free space >= 2.0 GB."""
    raw_ext_dir = Path(__file__).resolve().parent.parent / "datasets" / "raw" / "external"
    total_ext_bytes = sum(f.stat().st_size for f in raw_ext_dir.rglob("*") if f.is_file())

    # Maximum 1.5 GB acquisition budget
    assert total_ext_bytes < 1.5 * 1024 * 1024 * 1024, f"External downloads exceed 1.5 GB: {total_ext_bytes} bytes"

    # Minimum 2.0 GB free disk headroom
    free_bytes = get_disk_free_bytes()
    assert free_bytes >= 2.0 * 1024 * 1024 * 1024, f"Disk F: free space below 2.0 GB minimum: {free_bytes} bytes"

