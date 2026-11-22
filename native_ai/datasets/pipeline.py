"""Dataset Engineering Pipeline Orchestrator for LOVE Native AI.

Implements Tasks 1, 4, 6, 7, 8, 9, 10, 13, and 14:
- Ingests raw multi-category corpora streaming from native_ai/datasets/raw/
- Applies TextCleaner (Unicode, HTML artifacts, excessive whitespace, minimum length)
- Applies PrivacyFilter (PII redaction, secret rejection, confidential document filtering)
- Applies Deduplicator (Exact, normalized, and MinHash near-duplicate removal)
- Applies DatasetSplitter (Leakage-resistant Train 98%, Val 1%, Test 1% split)
- Saves split datasets to native_ai/datasets/splits/
- Produces full Quality Dashboard / Machine-readable Report in native_ai/datasets/reports/quality_report.json
- Preserves all manifests and checksums in native_ai/datasets/manifests/
"""
import sys
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from native_ai.datasets.source_registry import DatasetSourceRegistry
from native_ai.datasets.ingestion import DatasetIngestion
from native_ai.datasets.cleaning import TextCleaner
from native_ai.datasets.privacy_filter import PrivacyFilter
from native_ai.datasets.deduplication import Deduplicator
from native_ai.datasets.splitter import DatasetSplitter
from native_ai.datasets.curate_raw_sources import curate_and_write_sources

DATASETS_DIR = PROJECT_ROOT / "native_ai" / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
STAGED_DIR = DATASETS_DIR / "staged"
SPLITS_DIR = DATASETS_DIR / "splits"
MANIFESTS_DIR = DATASETS_DIR / "manifests"
REPORTS_DIR = DATASETS_DIR / "reports"


def run_dataset_pipeline() -> Dict[str, Any]:
    print("=" * 80)
    print("  LOVE NATIVE AI: DATASET ENGINEERING & QUALITY PIPELINE")
    print("=" * 80)

    # 1. Ensure Raw Corpora Exist
    raw_files = list(RAW_DIR.glob("*.jsonl"))
    if not raw_files:
        print("Raw JSONL corpora not found. Curating baseline corpora...")
        curate_and_write_sources()

    # 2. Source Registry
    registry = DatasetSourceRegistry()

    # 3. Initialize Pipeline Modules
    ingestor = DatasetIngestion()
    cleaner = TextCleaner(min_chars=40, min_words=8)
    privacy_filter = PrivacyFilter()
    deduplicator = Deduplicator(enable_near_dup=True, near_dup_threshold=0.85)
    splitter = DatasetSplitter(seed=42, train_ratio=0.98, val_ratio=0.01, test_ratio=0.01)

    # Telemetry Counters
    metrics = {
        "raw_documents_read": 0,
        "raw_bytes_read": 0,
        "cleaning_rejected": 0,
        "privacy_rejected": 0,
        "privacy_redactions": 0,
        "exact_duplicates_rejected": 0,
        "normalized_duplicates_rejected": 0,
        "near_duplicates_rejected": 0,
        "admitted_documents": 0,
        "admitted_bytes": 0,
        "admitted_words": 0,
        "category_distribution": {},
        "filter_rejection_reasons": {},
    }

    admitted_records: List[Dict[str, Any]] = []

    # Map raw files to source IDs
    source_map = {
        "general_english.jsonl": "src_gen_en_01",
        "reasoning_math.jsonl": "src_math_01",
        "instruction_dialog.jsonl": "src_dialog_01",
        "technical_code.jsonl": "src_tech_01",
        "structured_tasks.jsonl": "src_struct_01",
    }

    t0 = time.perf_counter()

    # 4. Stream & Process Each Source File
    for filename, source_id in source_map.items():
        file_path = RAW_DIR / filename
        if not file_path.exists():
            continue

        category = registry.sources[source_id].category
        file_doc_count = 0

        for raw_record in ingestor.stream_file(file_path, source_id=source_id, category=category):
            metrics["raw_documents_read"] += 1
            metrics["raw_bytes_read"] += raw_record["raw_bytes"]
            file_doc_count += 1

            raw_text = raw_record["text"]
            doc_id = raw_record["doc_id"]

            # Step A: Text Cleaning
            cleaned_text, clean_meta = cleaner.clean_text(raw_text)
            if cleaned_text is None:
                metrics["cleaning_rejected"] += 1
                reason = clean_meta.get("reason", "unknown_clean_rejection")
                metrics["filter_rejection_reasons"][reason] = metrics["filter_rejection_reasons"].get(reason, 0) + 1
                continue

            # Step B: Privacy & Secrets Filtering
            is_safe, sanitized_text, flags = privacy_filter.inspect_and_filter(cleaned_text)
            if not is_safe:
                metrics["privacy_rejected"] += 1
                for flag in flags:
                    metrics["filter_rejection_reasons"][flag] = metrics["filter_rejection_reasons"].get(flag, 0) + 1
                continue

            if flags:
                metrics["privacy_redactions"] += len(flags)

            # Step C: Deduplication (Exact, Normalized, Near-Duplicate)
            is_unique, dedup_meta = deduplicator.check_and_add(doc_id, sanitized_text)
            if not is_unique:
                reason = dedup_meta.get("reason", "duplicate")
                if reason == "exact_duplicate":
                    metrics["exact_duplicates_rejected"] += 1
                elif reason == "normalized_duplicate":
                    metrics["normalized_duplicates_rejected"] += 1
                elif reason == "near_duplicate":
                    metrics["near_duplicates_rejected"] += 1
                continue

            # Step D: Admit Record
            words_count = len(sanitized_text.split())
            bytes_count = len(sanitized_text.encode("utf-8"))

            record = {
                "doc_id": doc_id,
                "source_id": source_id,
                "category": category,
                "text": sanitized_text,
                "words": words_count,
                "bytes": bytes_count,
                "sha256": hashlib.sha256(sanitized_text.encode("utf-8")).hexdigest(),
            }
            admitted_records.append(record)
            metrics["admitted_documents"] += 1
            metrics["admitted_bytes"] += bytes_count
            metrics["admitted_words"] += words_count

            metrics["category_distribution"][category] = metrics["category_distribution"].get(category, 0) + 1

        registry.update_file_metadata(source_id, file_path, file_doc_count)

    duration = time.perf_counter() - t0

    # 5. Save Staged Full Dataset
    STAGED_DIR.mkdir(parents=True, exist_ok=True)
    staged_path = STAGED_DIR / "cleaned_corpus.jsonl"
    with open(staged_path, "w", encoding="utf-8") as f:
        for r in admitted_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 6. Split Dataset (Train 98%, Val 1%, Test 1%)
    train_set, val_set, test_set = splitter.split_records(admitted_records)
    split_manifests = splitter.save_splits(train_set, val_set, test_set, SPLITS_DIR, MANIFESTS_DIR)

    # 7. Update Source Registry
    registry.export_registry(MANIFESTS_DIR / "source_registry.json")

    # 8. Compute Distribution Percentages
    total_admitted = max(1, metrics["admitted_documents"])
    category_pct = {
        cat: round(count / total_admitted * 100, 2)
        for cat, count in metrics["category_distribution"].items()
    }

    # 9. Assemble Quality Report
    report = {
        "pipeline_version": "1.0.0",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processing_time_seconds": round(duration, 3),
        "documents": {
            "raw_ingested": metrics["raw_documents_read"],
            "cleaning_rejected": metrics["cleaning_rejected"],
            "privacy_rejected": metrics["privacy_rejected"],
            "exact_duplicates_rejected": metrics["exact_duplicates_rejected"],
            "normalized_duplicates_rejected": metrics["normalized_duplicates_rejected"],
            "near_duplicates_rejected": metrics["near_duplicates_rejected"],
            "total_duplicates_removed": (
                metrics["exact_duplicates_rejected"]
                + metrics["normalized_duplicates_rejected"]
                + metrics["near_duplicates_rejected"]
            ),
            "final_admitted": metrics["admitted_documents"],
            "retention_rate_pct": round(metrics["admitted_documents"] / max(1, metrics["raw_documents_read"]) * 100, 2),
        },
        "bytes": {
            "raw_bytes": metrics["raw_bytes_read"],
            "cleaned_bytes": metrics["admitted_bytes"],
            "compression_or_cleaning_delta_bytes": metrics["raw_bytes_read"] - metrics["admitted_bytes"],
        },
        "words": {
            "total_cleaned_words": metrics["admitted_words"],
            "avg_words_per_document": round(metrics["admitted_words"] / max(1, metrics["admitted_documents"]), 2),
        },
        "category_distribution": {
            "counts": metrics["category_distribution"],
            "percentages": category_pct,
            "target_proportions": {
                "general_english": 35.0,
                "reasoning_math": 20.0,
                "instruction_dialog": 20.0,
                "technical_code": 15.0,
                "structured_tasks": 10.0,
            }
        },
        "splits": {
            "train": split_manifests["train"],
            "validation": split_manifests["val"],
            "test": split_manifests["test"],
        },
        "filter_rejection_reasons": metrics["filter_rejection_reasons"],
        "privacy_redactions_applied": metrics["privacy_redactions"],
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / "quality_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nPipeline finished in {duration:.2f} seconds.")
    print(f"Raw Ingested: {metrics['raw_documents_read']} docs ({metrics['raw_bytes_read']:,} bytes)")
    print(f"Duplicates Removed: {report['documents']['total_duplicates_removed']}")
    print(f"Privacy/Cleaning Rejected: {metrics['privacy_rejected'] + metrics['cleaning_rejected']}")
    print(f"Final Admitted: {metrics['admitted_documents']} docs ({metrics['admitted_words']:,} words)")
    print(f"Splits Generated:")
    print(f"  Train: {len(train_set)} docs ({split_manifests['train']['num_words']:,} words)")
    print(f"  Val:   {len(val_set)} docs ({split_manifests['val']['num_words']:,} words)")
    print(f"  Test:  {len(test_set)} docs ({split_manifests['test']['num_words']:,} words)")
    print(f"Quality Report exported to: {report_file}")

    return report


if __name__ == "__main__":
    run_dataset_pipeline()
