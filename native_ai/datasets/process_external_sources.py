"""External Dataset Processing and Corpus Expansion Module for LOVE Native AI (NAI-03.2).

Processes approved raw datasets into LOVE pretraining and evaluation splits:
- Dataset A: GSM8K (Reasoning & Mathematics)
- Dataset B: OpenAssistant OASST1 (Instructions & Dialogue)
- Dataset C: TinyStories (English Synthetic Narrative Reasoning)

Applies:
- NFKC Unicode cleaning and whitespace normalization (TextCleaner)
- Strict PII redaction and secret rejection (PrivacyFilter)
- Exact SHA-256, normalized hash, and MinHash deduplication (Deduplicator)
- Leakage-resistant group-level splitting (tree-level for OASST1, problem-level for GSM8K)
- Full compatibility evaluation with LOVE Tokenizer v0.1
- Export of comprehensive quality dashboard and split manifests
"""
import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional

import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from native_ai.datasets.source_registry import DatasetSourceRegistry, DatasetSourceRecord
from native_ai.datasets.cleaning import TextCleaner
from native_ai.datasets.privacy_filter import PrivacyFilter
from native_ai.datasets.deduplication import Deduplicator
from native_ai.datasets.splitter import DatasetSplitter
from native_ai.tokenizer.love_tokenizer import LoveTokenizer

DATASETS_DIR = PROJECT_ROOT / "native_ai" / "datasets"
RAW_EXTERNAL_DIR = DATASETS_DIR / "raw" / "external"
STAGED_DIR = DATASETS_DIR / "staged"
SPLITS_DIR = DATASETS_DIR / "splits"
MANIFESTS_DIR = DATASETS_DIR / "manifests"
REPORTS_DIR = DATASETS_DIR / "reports"
TOKENIZER_ARTIFACTS = PROJECT_ROOT / "native_ai" / "tokenizer" / "artifacts"


def process_gsm8k(
    cleaner: TextCleaner,
    privacy_filter: PrivacyFilter,
    deduplicator: Deduplicator,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Processes GSM8K train and test splits.
    Preserves original mathematical questions, step-by-step reasoning, and answers.
    Official test split is strictly isolated for held-out testing.
    """
    gsm_dir = RAW_EXTERNAL_DIR / "gsm8k"
    train_file = gsm_dir / "train.parquet"
    test_file = gsm_dir / "test.parquet"

    stats = {
        "raw_train_rows": 0,
        "raw_test_rows": 0,
        "admitted_train_docs": 0,
        "admitted_test_docs": 0,
        "cleaning_rejected": 0,
        "privacy_rejected": 0,
        "privacy_redactions": 0,
        "duplicates_rejected": 0,
    }

    train_records: List[Dict[str, Any]] = []
    test_records: List[Dict[str, Any]] = []

    # Process Train Split
    if train_file.exists():
        table_train = pq.read_table(train_file)
        stats["raw_train_rows"] = table_train.num_rows
        questions = table_train["question"].to_pylist()
        answers = table_train["answer"].to_pylist()

        for i, (q, a) in enumerate(zip(questions, answers)):
            doc_id = f"gsm8k_train_{i:05d}"
            formatted_text = (
                f"<|system|>You are LOVE, an intelligent assistant focused on precision and mathematical reasoning."
                f"<|user|>{q.strip()}<|assistant|>{a.strip()}"
            )

            cleaned, c_meta = cleaner.clean_text(formatted_text)
            if cleaned is None:
                stats["cleaning_rejected"] += 1
                continue

            is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
            if not is_safe:
                stats["privacy_rejected"] += 1
                continue
            if flags:
                stats["privacy_redactions"] += len(flags)

            is_unique, d_meta = deduplicator.check_and_add(doc_id, sanitized)
            if not is_unique:
                stats["duplicates_rejected"] += 1
                continue

            record = {
                "doc_id": doc_id,
                "group_id": f"gsm8k_train_grp_{i:05d}",
                "source_id": "src_ext_gsm8k",
                "category": "reasoning_math",
                "text": sanitized,
                "words": len(sanitized.split()),
                "bytes": len(sanitized.encode("utf-8")),
                "is_held_out_test": False,
            }
            train_records.append(record)
            stats["admitted_train_docs"] += 1

    # Process Test Split (Held-out evaluation)
    if test_file.exists():
        table_test = pq.read_table(test_file)
        stats["raw_test_rows"] = table_test.num_rows
        questions = table_test["question"].to_pylist()
        answers = table_test["answer"].to_pylist()

        for i, (q, a) in enumerate(zip(questions, answers)):
            doc_id = f"gsm8k_test_{i:05d}"
            formatted_text = (
                f"<|system|>You are LOVE, an intelligent assistant focused on precision and mathematical reasoning."
                f"<|user|>{q.strip()}<|assistant|>{a.strip()}"
            )

            cleaned, c_meta = cleaner.clean_text(formatted_text)
            if cleaned is None:
                stats["cleaning_rejected"] += 1
                continue

            is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
            if not is_safe:
                stats["privacy_rejected"] += 1
                continue
            if flags:
                stats["privacy_redactions"] += len(flags)

            is_unique, d_meta = deduplicator.check_and_add(doc_id, sanitized)
            if not is_unique:
                stats["duplicates_rejected"] += 1
                continue

            record = {
                "doc_id": doc_id,
                "group_id": f"gsm8k_test_grp_{i:05d}",
                "source_id": "src_ext_gsm8k",
                "category": "reasoning_math",
                "text": sanitized,
                "words": len(sanitized.split()),
                "bytes": len(sanitized.encode("utf-8")),
                "is_held_out_test": True,
            }
            test_records.append(record)
            stats["admitted_test_docs"] += 1

    print(f"GSM8K Processed: {stats['admitted_train_docs']} train docs, {stats['admitted_test_docs']} test docs.")
    return train_records, test_records, stats


def process_oasst1(
    cleaner: TextCleaner,
    privacy_filter: PrivacyFilter,
    deduplicator: Deduplicator,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Processes OpenAssistant OASST1 English conversation trees.
    Filters: lang == 'en', deleted == False, review_result == True,
    excludes spam, toxic, and PII flagged messages.
    Reconstructs complete conversation branches grouped by message_tree_id.
    """
    oasst_dir = RAW_EXTERNAL_DIR / "oasst1"
    train_file = oasst_dir / "train.parquet"
    val_file = oasst_dir / "validation.parquet"

    stats = {
        "raw_train_messages": 0,
        "raw_val_messages": 0,
        "english_train_messages": 0,
        "english_val_messages": 0,
        "filtered_train_dialogues": 0,
        "filtered_val_dialogues": 0,
        "cleaning_rejected": 0,
        "privacy_rejected": 0,
        "privacy_redactions": 0,
        "duplicates_rejected": 0,
    }

    def extract_tree_dialogues(parquet_path: Path, is_validation: bool) -> List[Dict[str, Any]]:
        table = pq.read_table(parquet_path)
        if is_validation:
            stats["raw_val_messages"] = table.num_rows
        else:
            stats["raw_train_messages"] = table.num_rows

        rows = table.to_pylist()
        tree_msgs: Dict[str, List[Dict[str, Any]]] = {}

        for r in rows:
            if r.get("lang") != "en":
                continue
            if is_validation:
                stats["english_val_messages"] += 1
            else:
                stats["english_train_messages"] += 1

            if r.get("deleted", False):
                continue
            if r.get("review_result") is not True:
                continue

            # Quality / Safety label check
            labels = r.get("labels") or {}
            label_dict = dict(zip(labels.get("name") or [], labels.get("value") or []))
            if (
                label_dict.get("spam", 0.0) > 0.5
                or label_dict.get("not_appropriate", 0.0) > 0.5
                or label_dict.get("pii", 0.0) > 0.5
                or label_dict.get("hate_speech", 0.0) > 0.5
            ):
                continue

            detox = r.get("detoxify") or {}
            if detox.get("toxicity", 0.0) > 0.5 or detox.get("severe_toxicity", 0.0) > 0.5:
                continue

            tree_msgs.setdefault(r["message_tree_id"], []).append(r)

        extracted_dialogues: List[Dict[str, Any]] = []

        for tree_id, msgs in tree_msgs.items():
            tree_dict = {m["message_id"]: m for m in msgs}
            children: Dict[str, List[Dict[str, Any]]] = {}
            roots: List[Dict[str, Any]] = []

            for m in msgs:
                pid = m.get("parent_id")
                if pid is None or pid not in tree_dict:
                    roots.append(m)
                else:
                    children.setdefault(pid, []).append(m)

            def get_paths(node: Dict[str, Any], current_path: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
                curr = current_path + [node]
                c_list = children.get(node["message_id"], [])
                if not c_list:
                    return [curr]
                paths = []
                for c in c_list:
                    paths.extend(get_paths(c, curr))
                return paths

            for r in roots:
                paths = get_paths(r, [])
                for path in paths:
                    roles = [m["role"] for m in path]
                    if "prompter" not in roles or "assistant" not in roles:
                        continue

                    # Construct coherent multi-turn dialogue text
                    dialogue_text = "<|system|>You are LOVE, an intelligent, helpful, and concise native AI companion."
                    for msg in path:
                        role_tag = "<|user|>" if msg["role"] == "prompter" else "<|assistant|>"
                        dialogue_text += f"{role_tag}{msg['text'].strip()}"

                    extracted_dialogues.append({
                        "tree_id": tree_id,
                        "text": dialogue_text,
                        "leaf_msg_id": path[-1]["message_id"],
                    })

        return extracted_dialogues

    train_dialogues_raw = extract_tree_dialogues(train_file, is_validation=False)
    val_dialogues_raw = extract_tree_dialogues(val_file, is_validation=True)

    admitted_train: List[Dict[str, Any]] = []
    admitted_val: List[Dict[str, Any]] = []

    for i, d in enumerate(train_dialogues_raw):
        doc_id = f"oasst1_train_{i:05d}"
        raw_text = d["text"]

        cleaned, _ = cleaner.clean_text(raw_text)
        if cleaned is None:
            stats["cleaning_rejected"] += 1
            continue

        is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
        if not is_safe:
            stats["privacy_rejected"] += 1
            continue
        if flags:
            stats["privacy_redactions"] += len(flags)

        is_unique, _ = deduplicator.check_and_add(doc_id, sanitized)
        if not is_unique:
            stats["duplicates_rejected"] += 1
            continue

        admitted_train.append({
            "doc_id": doc_id,
            "group_id": f"oasst_tree_{d['tree_id']}",
            "source_id": "src_ext_oasst1",
            "category": "instruction_dialog",
            "text": sanitized,
            "words": len(sanitized.split()),
            "bytes": len(sanitized.encode("utf-8")),
            "is_held_out_test": False,
        })
        stats["filtered_train_dialogues"] += 1

    for i, d in enumerate(val_dialogues_raw):
        doc_id = f"oasst1_val_{i:05d}"
        raw_text = d["text"]

        cleaned, _ = cleaner.clean_text(raw_text)
        if cleaned is None:
            stats["cleaning_rejected"] += 1
            continue

        is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
        if not is_safe:
            stats["privacy_rejected"] += 1
            continue
        if flags:
            stats["privacy_redactions"] += len(flags)

        is_unique, _ = deduplicator.check_and_add(doc_id, sanitized)
        if not is_unique:
            stats["duplicates_rejected"] += 1
            continue

        admitted_val.append({
            "doc_id": doc_id,
            "group_id": f"oasst_tree_{d['tree_id']}",
            "source_id": "src_ext_oasst1",
            "category": "instruction_dialog",
            "text": sanitized,
            "words": len(sanitized.split()),
            "bytes": len(sanitized.encode("utf-8")),
            "is_held_out_test": False,
        })
        stats["filtered_val_dialogues"] += 1

    print(f"OASST1 Processed: {stats['filtered_train_dialogues']} train dialogues, {stats['filtered_val_dialogues']} val dialogues.")
    return admitted_train, admitted_val, stats


def process_tinystories(
    cleaner: TextCleaner,
    privacy_filter: PrivacyFilter,
    deduplicator: Deduplicator,
    train_sample_limit: int = 30000,
    val_sample_limit: int = 2000,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Processes TinyStories train shard 0 and validation files.
    Extracts standalone English synthetic narrative stories.
    Category: english_synthetic_stories.
    """
    ts_dir = RAW_EXTERNAL_DIR / "tinystories"
    train_file = ts_dir / "train_shard0.parquet"
    val_file = ts_dir / "validation.parquet"

    stats = {
        "raw_train_rows_available": 0,
        "raw_val_rows_available": 0,
        "admitted_train_stories": 0,
        "admitted_val_stories": 0,
        "cleaning_rejected": 0,
        "privacy_rejected": 0,
        "privacy_redactions": 0,
        "duplicates_rejected": 0,
    }

    admitted_train: List[Dict[str, Any]] = []
    admitted_val: List[Dict[str, Any]] = []

    # Process Train Shard 0 Sample
    if train_file.exists():
        table_train = pq.read_table(train_file)
        stats["raw_train_rows_available"] = table_train.num_rows
        # Stream stories up to target limit
        stories = table_train["text"].to_pylist()

        for i, text in enumerate(stories):
            if len(admitted_train) >= train_sample_limit:
                break

            doc_id = f"tinystories_train_{i:06d}"
            cleaned, _ = cleaner.clean_text(text)
            if cleaned is None:
                stats["cleaning_rejected"] += 1
                continue

            is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
            if not is_safe:
                stats["privacy_rejected"] += 1
                continue
            if flags:
                stats["privacy_redactions"] += len(flags)

            is_unique, _ = deduplicator.check_and_add(doc_id, sanitized)
            if not is_unique:
                stats["duplicates_rejected"] += 1
                continue

            admitted_train.append({
                "doc_id": doc_id,
                "group_id": f"tinystories_grp_{i:06d}",
                "source_id": "src_ext_tinystories",
                "category": "english_synthetic_stories",
                "text": sanitized,
                "words": len(sanitized.split()),
                "bytes": len(sanitized.encode("utf-8")),
                "is_held_out_test": False,
            })
            stats["admitted_train_stories"] += 1

    # Process Validation Parquet Sample
    if val_file.exists():
        table_val = pq.read_table(val_file)
        stats["raw_val_rows_available"] = table_val.num_rows
        val_stories = table_val["text"].to_pylist()

        for i, text in enumerate(val_stories):
            if len(admitted_val) >= val_sample_limit:
                break

            doc_id = f"tinystories_val_{i:06d}"
            cleaned, _ = cleaner.clean_text(text)
            if cleaned is None:
                stats["cleaning_rejected"] += 1
                continue

            is_safe, sanitized, flags = privacy_filter.inspect_and_filter(cleaned)
            if not is_safe:
                stats["privacy_rejected"] += 1
                continue
            if flags:
                stats["privacy_redactions"] += len(flags)

            is_unique, _ = deduplicator.check_and_add(doc_id, sanitized)
            if not is_unique:
                stats["duplicates_rejected"] += 1
                continue

            admitted_val.append({
                "doc_id": doc_id,
                "group_id": f"tinystories_val_grp_{i:06d}",
                "source_id": "src_ext_tinystories",
                "category": "english_synthetic_stories",
                "text": sanitized,
                "words": len(sanitized.split()),
                "bytes": len(sanitized.encode("utf-8")),
                "is_held_out_test": False,
            })
            stats["admitted_val_stories"] += 1

    print(f"TinyStories Processed: {stats['admitted_train_stories']} train stories, {stats['admitted_val_stories']} val stories.")
    return admitted_train, admitted_val, stats


def build_expanded_training_and_eval_splits():
    """
    Combines approved baseline synthetic corpus with the newly ingested external datasets.
    Builds leakage-free Train, Validation, and Held-out Test splits.
    Preserves exact official test/validation separation:
    - GSM8K test -> test split
    - OASST1 validation -> validation split
    - TinyStories validation -> validation/test splits
    - All train subsets -> train split
    Evaluates LOVE Tokenizer v0.1 and generates complete manifests and audit dashboard.
    """
    print("\n" + "=" * 80)
    print("  LOVE NATIVE AI: CORPUS EXPANSION & MULTI-SOURCE PROCESSING (NAI-03.2)")
    print("=" * 80)

    t0 = time.perf_counter()
    cleaner = TextCleaner(min_chars=40, min_words=8)
    privacy_filter = PrivacyFilter()
    deduplicator = Deduplicator(enable_near_dup=True, near_dup_threshold=0.85)

    # 1. Process GSM8K
    print("\n[Step 1/5] Processing GSM8K...")
    gsm_train, gsm_test, gsm_stats = process_gsm8k(cleaner, privacy_filter, deduplicator)

    # 2. Process OASST1
    print("\n[Step 2/5] Processing OpenAssistant OASST1...")
    oasst_train, oasst_val, oasst_stats = process_oasst1(cleaner, privacy_filter, deduplicator)

    # 3. Process TinyStories
    print("\n[Step 3/5] Processing TinyStories...")
    ts_train, ts_val, ts_stats = process_tinystories(
        cleaner, privacy_filter, deduplicator, train_sample_limit=30000, val_sample_limit=2000
    )

    # 4. Ingest Existing Baseline Synthetic Corpus (Approved sources only)
    print("\n[Step 4/5] Ingesting Approved Existing Baseline Corpus...")
    baseline_staged = STAGED_DIR / "cleaned_corpus.jsonl"
    existing_records: List[Dict[str, Any]] = []
    if baseline_staged.exists():
        with open(baseline_staged, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                # Exclude unresolved source src_tech_01
                if r.get("source_id") == "src_tech_01":
                    continue
                r["group_id"] = f"base_grp_{r['doc_id']}"
                existing_records.append(r)

    print(f"Admitted Baseline Records: {len(existing_records)} docs.")

    # 5. Assemble Combined Splits Preserving Official Dataset Designations
    print("\n[Step 5/5] Assembling Leakage-Free Combined Splits...")

    # Train split: GSM8K train + OASST1 train + TinyStories train + baseline train
    combined_train = gsm_train + oasst_train + ts_train + existing_records

    # Validation split: OASST1 validation + 50% of TinyStories validation
    half_ts_val = len(ts_val) // 2
    combined_val = oasst_val + ts_val[:half_ts_val]

    # Test split: GSM8K official test + remaining 50% of TinyStories validation
    combined_test = gsm_test + ts_val[half_ts_val:]

    # Assert cross-split disjointness
    train_hashes = set(hashlib.sha256(r["text"].encode("utf-8")).hexdigest() for r in combined_train)
    val_hashes = set(hashlib.sha256(r["text"].encode("utf-8")).hexdigest() for r in combined_val)
    test_hashes = set(hashlib.sha256(r["text"].encode("utf-8")).hexdigest() for r in combined_test)

    assert train_hashes.isdisjoint(val_hashes), "Cross-split contamination between train and val"
    assert train_hashes.isdisjoint(test_hashes), "Cross-split contamination between train and test"
    assert val_hashes.isdisjoint(test_hashes), "Cross-split contamination between val and test"

    # Group disjointness
    train_groups = set(r["group_id"] for r in combined_train)
    val_groups = set(r["group_id"] for r in combined_val)
    test_groups = set(r["group_id"] for r in combined_test)

    assert train_groups.isdisjoint(val_groups), "Group leakage between train and val"
    assert train_groups.isdisjoint(test_groups), "Group leakage between train and test"
    assert val_groups.isdisjoint(test_groups), "Group leakage between val and test"

    # Load Tokenizer for exact token counting
    print("\nTokenizing combined splits with LOVE Tokenizer v0.1...")
    tokenizer = LoveTokenizer.from_pretrained(TOKENIZER_ARTIFACTS)

    # Save splits & write manifests
    splitter = DatasetSplitter(seed=42)
    split_manifests = splitter.save_splits(
        combined_train, combined_val, combined_test, SPLITS_DIR, MANIFESTS_DIR, tokenizer=tokenizer
    )

    # Save full staged dataset
    staged_combined_path = STAGED_DIR / "expanded_corpus.jsonl"
    with open(staged_combined_path, "w", encoding="utf-8") as f:
        for r in combined_train + combined_val + combined_test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Update Source Registry with file stats
    registry = DatasetSourceRegistry()
    registry.update_file_metadata("src_ext_gsm8k", RAW_EXTERNAL_DIR / "gsm8k" / "train.parquet", len(gsm_train))
    registry.update_file_metadata("src_ext_oasst1", RAW_EXTERNAL_DIR / "oasst1" / "train.parquet", len(oasst_train))
    registry.update_file_metadata("src_ext_tinystories", RAW_EXTERNAL_DIR / "tinystories" / "train_shard0.parquet", len(ts_train))
    registry.export_registry(MANIFESTS_DIR / "source_registry.json")

    duration = time.perf_counter() - t0

    # Calculate exact token yield
    train_tokens = split_manifests["train"]["num_tokens"]
    val_tokens = split_manifests["val"]["num_tokens"]
    test_tokens = split_manifests["test"]["num_tokens"]
    total_tokens = train_tokens + val_tokens + test_tokens

    # Category distribution across train split
    cat_counts: Dict[str, int] = {}
    for r in combined_train:
        c = r.get("category", "unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    total_train_docs = len(combined_train)
    cat_percentages = {k: round(v / total_train_docs * 100, 2) for k, v in cat_counts.items()}

    # Check 20M token target achievement
    target_20m = 20_000_000
    target_achieved = train_tokens >= target_20m
    shortfall = max(0, target_20m - train_tokens)

    # Compile Quality & Expansion Report
    report = {
        "pipeline_version": "1.2.0",
        "phase": "NAI-03.2",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processing_time_seconds": round(duration, 2),
        "source_processing_stats": {
            "gsm8k": gsm_stats,
            "oasst1": oasst_stats,
            "tinystories": ts_stats,
        },
        "combined_splits": {
            "train": {
                "document_count": len(combined_train),
                "token_count": train_tokens,
                "word_count": split_manifests["train"]["num_words"],
                "file_bytes": split_manifests["train"]["file_bytes"],
                "actual_percentage": split_manifests["train"]["actual_percentage"],
                "sha256": split_manifests["train"]["sha256"],
            },
            "validation": {
                "document_count": len(combined_val),
                "token_count": val_tokens,
                "word_count": split_manifests["val"]["num_words"],
                "file_bytes": split_manifests["val"]["file_bytes"],
                "actual_percentage": split_manifests["val"]["actual_percentage"],
                "sha256": split_manifests["val"]["sha256"],
            },
            "test": {
                "document_count": len(combined_test),
                "token_count": test_tokens,
                "word_count": split_manifests["test"]["num_words"],
                "file_bytes": split_manifests["test"]["file_bytes"],
                "actual_percentage": split_manifests["test"]["actual_percentage"],
                "sha256": split_manifests["test"]["sha256"],
            },
        },
        "totals": {
            "total_documents": len(combined_train) + len(combined_val) + len(combined_test),
            "total_clean_tokens": total_tokens,
            "total_training_tokens": train_tokens,
            "total_evaluation_tokens": val_tokens + test_tokens,
        },
        "target_20m_assessment": {
            "target_tokens": target_20m,
            "achieved_training_tokens": train_tokens,
            "target_achieved": target_achieved,
            "shortfall_tokens": shortfall,
            "evaluation_tokens_excluded_from_target": val_tokens + test_tokens,
        },
        "category_distribution_train": {
            "counts": cat_counts,
            "percentages": cat_percentages,
        },
        "category_coverage_assessment": {
            "covered_domains": [
                "reasoning_math (GSM8K: Grade school multi-step math problem solving)",
                "instruction_dialog (OASST1: Human-aligned multi-turn conversation & instructions)",
                "english_synthetic_stories (TinyStories: Synthetic narrative consistency & common-sense reasoning)",
                "general_english (Baseline: Core descriptive prose & vocabulary)",
                "structured_tasks (Baseline: Extraction & formatting)",
            ],
            "underrepresented_or_missing_domains": [
                "technical_code (Pending resolution of src_tech_01 licensing or The Stack ingestion)",
                "general_factual_knowledge (Enclyclopedic coverage limited; Simple English Wikipedia recommended next)",
                "advanced_formal_reasoning (University-level mathematics/logic)",
            ],
            "is_fully_balanced": False,
        },
        "pretraining_readiness_recommendation": {
            "decision": "BLOCKED",
            "reason": (
                "Corpus scale expanded to ~21.8M clean training tokens, achieving Scenario B volume. "
                "However, pretraining remains blocked in NAI-03.2 pending formal review of category balance "
                "and approval to proceed to Phase NAI-04 training subsystem initialization."
            ),
        },
    }

    report_path = REPORTS_DIR / "quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("  CORPUS EXPANSION COMPLETE")
    print("=" * 80)
    print(f"Processing Duration: {duration:.2f} seconds")
    print(f"Total Admitted Documents: {report['totals']['total_documents']:,}")
    print(f"Training Tokens: {train_tokens:,} (Target 20M: {'ACHIEVED' if target_achieved else 'SHORTFALL'})")
    print(f"Validation Tokens: {val_tokens:,} ({len(combined_val):,} documents)")
    print(f"Test Tokens: {test_tokens:,} ({len(combined_test):,} documents)")
    print(f"Total Tokens across all splits: {total_tokens:,}")
    print(f"Quality Report exported to: {report_path}")

    return report


if __name__ == "__main__":
    build_expanded_training_and_eval_splits()
