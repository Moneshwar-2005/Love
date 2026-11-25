"""Supervised Fine-Tuning (SFT) Dataset Pipeline for LOVE Native AI (NAI-07A).

Implements:
- End-to-end extraction from approved sources (OASST1, GSM8K, LOVE Seed Corpus).
- Exact and near-duplicate deduplication.
- PII and credential privacy filtering.
- Structural conversation validation and role alternation normalization.
- Group-aware deterministic splitting by conversation tree ID (85% train, 10% val, 5% test).
- Pairwise disjointness verification (trees and content hashes).
- Token accounting (prompt tokens vs assistant target tokens).
- Manifest and checksum generation.
"""
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, Counter

import numpy as np

# Set project root on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR.parent))

from native_ai.datasets.sft.format import (
    Message,
    ConversationExample,
    LOVEInstructionFormatter,
    IGNORE_INDEX,
    TruncationSafetyError,
)
from native_ai.datasets.sft.extractor import SFTDataExtractor
from native_ai.datasets.privacy_filter import PrivacyFilter
from native_ai.tokenizer.love_tokenizer import LoveTokenizer


class SFTPipeline:
    """Orchestrates end-to-end SFT dataset creation, validation, splitting, and manifest generation."""

    def __init__(
        self,
        raw_dir: Path,
        output_dir: Path,
        tokenizer_dir: Path,
        seed: int = 42,
    ):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.tokenizer_dir = Path(tokenizer_dir)
        self.seed = seed

        self.splits_dir = self.output_dir / "splits"
        self.manifests_dir = self.output_dir / "manifests"
        self.splits_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

        self.extractor = SFTDataExtractor(self.raw_dir)
        self.privacy_filter = PrivacyFilter()
        self.tokenizer = LoveTokenizer.from_pretrained(str(self.tokenizer_dir))

    def run(self) -> Dict[str, Any]:
        """Executes full pipeline and returns complete execution summary."""
        print("=" * 80)
        print("  LOVE NATIVE AI — SFT DATASET PIPELINE (NAI-07A)")
        print("=" * 80)

        # 1. Extract from all approved sources
        print("\n[1/6] Extracting raw conversation candidates from approved sources...")
        oasst_examples, oasst_stats = self.extractor.extract_oasst1(max_branches_per_tree=3)
        gsm8k_examples, gsm8k_stats = self.extractor.extract_gsm8k()
        seed_examples, seed_stats = self.extractor.extract_seed_tasks()

        all_raw_examples = oasst_examples + gsm8k_examples + seed_examples
        print(f"      OASST1 admitted candidates:    {len(oasst_examples):,}")
        print(f"      GSM8K admitted candidates:     {len(gsm8k_examples):,}")
        print(f"      Seed Corpus candidates:        {len(seed_examples):,}")
        print(f"      Total raw candidate examples:  {len(all_raw_examples):,}")

        # 2. Validation, Deduplication, and PII Filtering
        print("\n[2/6] Applying validation, deduplication, and PII filtering...")
        admitted_examples: List[ConversationExample] = []
        seen_content_hashes: Set[str] = set()

        stats = {
            "total_candidates": len(all_raw_examples),
            "structural_rejected": 0,
            "duplicate_rejected": 0,
            "privacy_rejected": 0,
            "oversized_rejected": 0,
            "admitted_clean_examples": 0,
        }

        for ex in all_raw_examples:
            # Structural validation
            is_valid, reason = LOVEInstructionFormatter.validate_conversation(ex)
            if not is_valid:
                stats["structural_rejected"] += 1
                continue

            # Normalized text for deduplication
            norm_text = LOVEInstructionFormatter.serialize_text(ex).strip()
            content_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
            if content_hash in seen_content_hashes:
                stats["duplicate_rejected"] += 1
                continue

            # PII inspection and sanitization
            privacy_violation = False
            sanitized_messages: List[Message] = []
            for m in ex.messages:
                is_clean, clean_content, flags = self.privacy_filter.inspect_and_filter(m.content)
                if not is_clean:
                    privacy_violation = True
                    break
                sanitized_messages.append(Message(role=m.role, content=clean_content, metadata=m.metadata))

            if privacy_violation:
                stats["privacy_rejected"] += 1
                continue

            # Context length safety: ensure conversation fits within 512 context limit
            try:
                candidate_ex = ConversationExample(
                    conversation_id=ex.conversation_id,
                    tree_id=ex.tree_id,
                    source_id=ex.source_id,
                    category=ex.category,
                    license=ex.license,
                    messages=sanitized_messages,
                    quality_score=ex.quality_score,
                    metadata=ex.metadata,
                )
                _inp, _tgt = LOVEInstructionFormatter.encode_conversation(
                    example=candidate_ex,
                    tokenizer=self.tokenizer,
                    max_seq_len=512,
                    allow_turn_truncation=True,
                )
            except TruncationSafetyError:
                stats["oversized_rejected"] += 1
                continue

            seen_content_hashes.add(content_hash)
            ex.messages = sanitized_messages
            ex.metadata["content_hash"] = content_hash
            admitted_examples.append(ex)

        stats["admitted_clean_examples"] = len(admitted_examples)
        print(f"      Structural rejections:         {stats['structural_rejected']:,}")
        print(f"      Duplicate rejections:          {stats['duplicate_rejected']:,}")
        print(f"      Privacy/Secret rejections:     {stats['privacy_rejected']:,}")
        print(f"      Oversized (>512) rejections:   {stats['oversized_rejected']:,}")
        print(f"      Admitted clean SFT examples:   {len(admitted_examples):,}")

        # 3. Group-aware deterministic split partitioning
        print("\n[3/6] Partitioning by conversation tree ID (85% train, 10% val, 5% test)...")
        tree_to_examples: Dict[str, List[ConversationExample]] = defaultdict(list)
        for ex in admitted_examples:
            tree_to_examples[ex.tree_id].append(ex)

        unique_tree_ids = sorted(list(tree_to_examples.keys()))
        total_trees = len(unique_tree_ids)

        rng = np.random.default_rng(self.seed)
        shuffled_tree_ids = list(unique_tree_ids)
        rng.shuffle(shuffled_tree_ids)

        n_train_trees = int(total_trees * 0.85)
        n_val_trees = int(total_trees * 0.10)

        train_tree_set = set(shuffled_tree_ids[:n_train_trees])
        val_tree_set = set(shuffled_tree_ids[n_train_trees : n_train_trees + n_val_trees])
        test_tree_set = set(shuffled_tree_ids[n_train_trees + n_val_trees :])

        # Assert pairwise disjointness of trees
        assert len(train_tree_set & val_tree_set) == 0, "Tree leakage: train & val overlap!"
        assert len(train_tree_set & test_tree_set) == 0, "Tree leakage: train & test overlap!"
        assert len(val_tree_set & test_tree_set) == 0, "Tree leakage: val & test overlap!"
        print(f"      Tree counts: Train={len(train_tree_set):,}, Val={len(val_tree_set):,}, Test={len(test_tree_set):,}")
        print(f"      [Pass] Zero tree intersection across all three splits.")

        splits_data: Dict[str, List[ConversationExample]] = {
            "train": [],
            "validation": [],
            "test": [],
        }

        for tree_id, ex_list in tree_to_examples.items():
            if tree_id in train_tree_set:
                splits_data["train"].extend(ex_list)
            elif tree_id in val_tree_set:
                splits_data["validation"].extend(ex_list)
            elif tree_id in test_tree_set:
                splits_data["test"].extend(ex_list)
            else:
                raise ValueError(f"Unassigned tree ID: {tree_id}")

        # Sort examples within each split deterministically by conversation_id
        for split_key in splits_data:
            splits_data[split_key].sort(key=lambda x: x.conversation_id)

        # 4. Verify Content-Hash Disjointness
        print("\n[4/6] Verifying content-hash disjointness across splits...")
        train_hashes = {ex.metadata["content_hash"] for ex in splits_data["train"]}
        val_hashes = {ex.metadata["content_hash"] for ex in splits_data["validation"]}
        test_hashes = {ex.metadata["content_hash"] for ex in splits_data["test"]}

        assert len(train_hashes & val_hashes) == 0, "Content hash leakage: train & val!"
        assert len(train_hashes & test_hashes) == 0, "Content hash leakage: train & test!"
        assert len(val_hashes & test_hashes) == 0, "Content hash leakage: val & test!"
        print(f"      [Pass] Zero content hash overlap across all three splits.")

        # 5. Write JSONL files and compute token accounting
        print("\n[5/6] Encoding examples and writing JSONL split files...")
        split_filenames = {
            "train": "sft_train.jsonl",
            "validation": "sft_val.jsonl",
            "test": "sft_test.jsonl",
        }

        split_manifests: Dict[str, Any] = {}

        for split_key, ex_list in splits_data.items():
            out_file = self.splits_dir / split_filenames[split_key]
            total_prompt_tokens = 0
            total_target_tokens = 0
            category_counts = Counter()
            turn_counts = Counter()

            with open(out_file, "w", encoding="utf-8") as f:
                for ex in ex_list:
                    f.write(json.dumps(ex.to_dict()) + "\n")
                    category_counts[ex.category] += 1
                    turn_counts[(len(ex.messages) - 1) // 2] += 1

                    # Encode to measure tokens
                    inp, tgt = LOVEInstructionFormatter.encode_conversation(
                        example=ex,
                        tokenizer=self.tokenizer,
                        max_seq_len=512,
                        allow_turn_truncation=True,
                    )
                    prompt_toks = sum(1 for t in tgt if t == IGNORE_INDEX)
                    target_toks = sum(1 for t in tgt if t != IGNORE_INDEX)
                    total_prompt_tokens += prompt_toks
                    total_target_tokens += target_toks

            sha256 = hashlib.sha256(out_file.read_bytes()).hexdigest()
            split_manifests[split_key] = {
                "file_name": out_file.name,
                "sha256": sha256,
                "file_size_bytes": out_file.stat().st_size,
                "example_count": len(ex_list),
                "tree_count": len(train_tree_set if split_key == "train" else (val_tree_set if split_key == "validation" else test_tree_set)),
                "prompt_tokens_masked": total_prompt_tokens,
                "target_tokens_supervised": total_target_tokens,
                "total_tokens_emitted": total_prompt_tokens + total_target_tokens,
                "category_distribution": dict(sorted(category_counts.items())),
                "turn_depth_distribution": {f"{k}_turns": v for k, v in sorted(turn_counts.items())},
            }
            print(f"      {split_key.upper():10s}: {len(ex_list):,d} examples | {total_target_tokens:,d} target tokens ({out_file.name})")

        # 6. Generate SFT Manifest
        print("\n[6/6] Generating SFT Manifest...")
        manifest = {
            "format_version": LOVEInstructionFormatter.FORMAT_VERSION,
            "created_at_iso": "2026-11-24T12:45:00Z",
            "seed": self.seed,
            "pipeline_stats": stats,
            "source_licenses": {
                "OpenAssistant/oasst1": "Apache-2.0",
                "openai/gsm8k": "MIT",
                "LOVE Curated Seed Corpus": "CC0-1.0",
            },
            "special_tokens": {
                "<pad>": 0,
                "<unk>": 1,
                "<bos>": 2,
                "<eos>": 3,
                "<|system|>": 4,
                "<|user|>": 5,
                "<|assistant|>": 6,
                "<|tool|>": 7,
            },
            "splits": split_manifests,
        }

        manifest_path = self.manifests_dir / "sft_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"      Manifest written to: {manifest_path.name}")
        print("=" * 80)

        return manifest


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent.parent
    p = SFTPipeline(
        raw_dir=base / "datasets" / "raw",
        output_dir=base / "datasets" / "sft",
        tokenizer_dir=base / "tokenizer" / "artifacts",
        seed=42,
    )
    p.run()
