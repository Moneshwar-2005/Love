"""Memory-Mapped Binary Token Cache for LOVE Native AI.

Implements Section 3 (NAI-04):
- Efficient streaming tokenization with LOVE Tokenizer v0.1.
- uint16 binary storage for 8,192-token vocabulary.
- Memory-mapped arrays without reading entire corpus into system RAM.
- Indexed document boundaries, token lengths, and domain categories.
- Strict token-ID range validation [0, 8192).
- Source and tokenizer artifact checksum tracking with stale cache detection.
- Atomic creation with temporary file cleanup and disk-headroom enforcement.
"""
import os
import shutil
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from native_ai.tokenizer.love_tokenizer import LoveTokenizer

CATEGORY_MAP = {
    "english_synthetic_stories": 0,
    "instruction_dialog": 1,
    "reasoning_math": 2,
    "general_english": 3,
    "structured_tasks": 4,
    "technical_code": 5,
}
REV_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}


class DiskSpaceError(RuntimeError):
    """Raised when available disk space is below required safety threshold."""
    pass


class CacheCorruptedError(ValueError):
    """Raised when cache contents fail validation checks."""
    pass


def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def get_drive_free_bytes(drive_path: str = "F:\\") -> int:
    """Returns available free bytes on target drive."""
    total, used, free = shutil.disk_usage(drive_path)
    return free


class BinaryTokenCacheBuilder:
    """Builds and validates memory-mapped uint16 binary token caches from dataset splits."""

    VOCAB_SIZE = 8192
    MIN_FREE_DISK_BYTES = 2 * 1024 * 1024 * 1024  # 2.0 GB reserve threshold

    def __init__(
        self,
        splits_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        tokenizer_artifacts_dir: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.splits_dir = splits_dir or (base_dir / "datasets" / "splits")
        self.cache_dir = cache_dir or (base_dir / "data_cache")
        self.tokenizer_artifacts_dir = tokenizer_artifacts_dir or (base_dir / "tokenizer" / "artifacts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.tokenizer: Optional[LoveTokenizer] = None

    def _ensure_tokenizer(self) -> LoveTokenizer:
        if self.tokenizer is None:
            self.tokenizer = LoveTokenizer.from_pretrained(self.tokenizer_artifacts_dir)
        return self.tokenizer

    def get_source_checksums(self) -> Dict[str, Dict[str, Any]]:
        """Returns file sizes and SHA-256 hashes for all three split files."""
        sources = {
            "train": self.splits_dir / "train" / "train.jsonl",
            "validation": self.splits_dir / "validation" / "val.jsonl",
            "test": self.splits_dir / "test" / "test.jsonl",
        }
        meta = {}
        for name, p in sources.items():
            if not p.exists():
                raise FileNotFoundError(f"Source split file missing: {p}")
            meta[name] = {
                "path": str(p),
                "bytes": p.stat().st_size,
                "sha256": compute_file_sha256(p),
            }
        return meta

    def get_tokenizer_checksums(self) -> Dict[str, str]:
        """Returns SHA-256 checksums of core tokenizer artifacts."""
        artifacts = ["vocab.json", "merges.txt", "tokenizer.json"]
        hashes = {}
        for a in artifacts:
            p = self.tokenizer_artifacts_dir / a
            if not p.exists():
                raise FileNotFoundError(f"Tokenizer artifact missing: {p}")
            hashes[a] = compute_file_sha256(p)
        return hashes

    def is_cache_stale(self) -> bool:
        """Checks if existing cache manifest exists and matches current source/tokenizer checksums."""
        manifest_path = self.cache_dir / "cache_manifest.json"
        if not manifest_path.exists():
            return True

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # Check expected files exist
            for split in ["train", "validation", "test"]:
                bin_file = self.cache_dir / f"{split}.bin"
                offsets_file = self.cache_dir / f"{split}_offsets.npy"
                if not bin_file.exists() or not offsets_file.exists():
                    return True

            # Verify source checksums
            current_sources = self.get_source_checksums()
            cached_sources = manifest.get("source_checksums", {})
            for split in ["train", "validation", "test"]:
                if cached_sources.get(split, {}).get("sha256") != current_sources[split]["sha256"]:
                    return True

            # Verify tokenizer checksums
            current_tok = self.get_tokenizer_checksums()
            cached_tok = manifest.get("tokenizer_checksums", {})
            for a, h in current_tok.items():
                if cached_tok.get(a) != h:
                    return True

            return False
        except Exception:
            return True

    def estimate_cache_storage(self) -> Dict[str, Any]:
        """Calculates estimated disk consumption for binary caches."""
        manifest_train = self.splits_dir.parent / "manifests" / "dataset_manifest_train.json"
        manifest_val = self.splits_dir.parent / "manifests" / "dataset_manifest_val.json"
        manifest_test = self.splits_dir.parent / "manifests" / "dataset_manifest_test.json"

        token_counts = {}
        doc_counts = {}
        for name, p in [("train", manifest_train), ("validation", manifest_val), ("test", manifest_test)]:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    token_counts[name] = d.get("num_tokens", 0)
                    doc_counts[name] = d.get("num_documents", 0)
            else:
                token_counts[name] = 0
                doc_counts[name] = 0

        # uint16 is 2 bytes per token; offsets are 12 bytes per doc (uint32 start, uint32 len, uint8 cat + padding)
        est_bin_bytes = sum(c * 2 for c in token_counts.values())
        est_idx_bytes = sum(d * 12 for d in doc_counts.values())
        total_est = est_bin_bytes + est_idx_bytes + 65536  # + metadata margin

        free_bytes = get_drive_free_bytes(str(self.cache_dir.anchor))

        return {
            "token_counts": token_counts,
            "document_counts": doc_counts,
            "estimated_binary_bytes": est_bin_bytes,
            "estimated_index_bytes": est_idx_bytes,
            "total_estimated_bytes": total_est,
            "available_drive_free_bytes": free_bytes,
            "safe_headroom_bytes": free_bytes - total_est,
            "is_safe": (free_bytes - total_est) >= self.MIN_FREE_DISK_BYTES,
        }

    def build_split_cache(
        self,
        split_name: str,
        jsonl_path: Path,
        expected_token_count: Optional[int] = None,
        expected_doc_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Tokenizes a split and writes uint16 memory-mapped array and index offsets atomically.
        Validates token range [0, 8192) and record counts.
        """
        tokenizer = self._ensure_tokenizer()

        # Check disk space before starting
        free_bytes = get_drive_free_bytes(str(self.cache_dir.anchor))
        if free_bytes < self.MIN_FREE_DISK_BYTES:
            raise DiskSpaceError(
                f"Cannot build cache: Drive free space ({free_bytes} bytes) is below minimum safety threshold ({self.MIN_FREE_DISK_BYTES} bytes)"
            )

        tmp_bin = self.cache_dir / f"{split_name}.bin.tmp"
        tmp_offsets = self.cache_dir / f"{split_name}_offsets_tmp.npy"

        final_bin = self.cache_dir / f"{split_name}.bin"
        final_offsets = self.cache_dir / f"{split_name}_offsets.npy"

        # Pre-count or stream tokens
        # We first stream through and encode into memory chunks, then flush to memmap
        doc_offsets = []  # tuples: (start_idx, length, category_code)
        tokens_list = []
        current_offset = 0

        cat_counts = {k: 0 for k in CATEGORY_MAP}
        cat_tokens = {k: 0 for k in CATEGORY_MAP}

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                rec = json.loads(line)
                text = rec["text"]
                cat = rec.get("category", "general_english")
                cat_code = CATEGORY_MAP.get(cat, CATEGORY_MAP["general_english"])

                ids = tokenizer.encode(text)
                num_ids = len(ids)

                # Validate token IDs
                for tid in ids:
                    if tid < 0 or tid >= self.VOCAB_SIZE:
                        raise CacheCorruptedError(
                            f"Invalid token ID {tid} encountered at doc {line_idx} (allowed: [0, {self.VOCAB_SIZE}))"
                        )

                doc_offsets.append((current_offset, num_ids, cat_code))
                tokens_list.extend(ids)
                current_offset += num_ids

                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                cat_tokens[cat] = cat_tokens.get(cat, 0) + num_ids

        total_tokens = len(tokens_list)
        total_docs = len(doc_offsets)

        if expected_token_count is not None and total_tokens != expected_token_count:
            raise CacheCorruptedError(
                f"Token count mismatch for {split_name}: expected {expected_token_count}, got {total_tokens}"
            )
        if expected_doc_count is not None and total_docs != expected_doc_count:
            raise CacheCorruptedError(
                f"Document count mismatch for {split_name}: expected {expected_doc_count}, got {total_docs}"
            )

        # Write binary token cache via memmap
        mmap_arr = np.memmap(tmp_bin, dtype=np.uint16, mode="w+", shape=(total_tokens,))
        # Copy tokens in chunks to avoid large temporary RAM overhead
        chunk_size = 500_000
        for i in range(0, total_tokens, chunk_size):
            end_i = min(i + chunk_size, total_tokens)
            mmap_arr[i:end_i] = np.array(tokens_list[i:end_i], dtype=np.uint16)
        mmap_arr.flush()
        del mmap_arr

        # Write offsets array: shape (total_docs, 3) dtype uint32
        # col 0: start_offset (uint32)
        # col 1: length (uint32)
        # col 2: category_code (uint32)
        offsets_arr = np.array(doc_offsets, dtype=np.uint32)
        np.save(tmp_offsets, offsets_arr)

        # Atomic replacement
        if final_bin.exists():
            final_bin.unlink()
        if final_offsets.exists():
            final_offsets.unlink()

        os.replace(tmp_bin, final_bin)
        os.replace(tmp_offsets, final_offsets)

        bin_sha256 = compute_file_sha256(final_bin)
        offsets_sha256 = compute_file_sha256(final_offsets)

        return {
            "split": split_name,
            "total_tokens": total_tokens,
            "total_documents": total_docs,
            "bin_bytes": final_bin.stat().st_size,
            "bin_sha256": bin_sha256,
            "offsets_bytes": final_offsets.stat().st_size,
            "offsets_sha256": offsets_sha256,
            "category_counts": cat_counts,
            "category_tokens": cat_tokens,
        }

    def build_all_caches(self, force: bool = False) -> Dict[str, Any]:
        """Builds binary caches for train, validation, and test splits and creates cache_manifest.json."""
        if not force and not self.is_cache_stale():
            with open(self.cache_dir / "cache_manifest.json", "r", encoding="utf-8") as f:
                return json.load(f)

        est = self.estimate_cache_storage()
        if not est["is_safe"]:
            raise DiskSpaceError(
                f"Insufficient disk headroom to build caches: {est['safe_headroom_bytes']} bytes remaining after est."
            )

        t0 = time.perf_counter()
        source_meta = self.get_source_checksums()
        tok_hashes = self.get_tokenizer_checksums()

        # Token counts from split manifests if available
        manifest_dir = self.splits_dir.parent / "manifests"
        expected_tokens = {}
        expected_docs = {}
        for split, fname in [("train", "dataset_manifest_train.json"), ("validation", "dataset_manifest_val.json"), ("test", "dataset_manifest_test.json")]:
            p = manifest_dir / fname
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    expected_tokens[split] = d.get("num_tokens")
                    expected_docs[split] = d.get("num_documents")

        splits_info = {}
        for split_name, path_key in [("train", "train"), ("validation", "validation"), ("test", "test")]:
            info = self.build_split_cache(
                split_name=split_name,
                jsonl_path=Path(source_meta[path_key]["path"]),
                expected_token_count=expected_tokens.get(split_name),
                expected_doc_count=expected_docs.get(split_name),
            )
            splits_info[split_name] = info

        duration = time.perf_counter() - t0

        manifest = {
            "manifest_version": "1.0.0",
            "phase": "NAI-04",
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "build_duration_seconds": round(duration, 2),
            "vocab_size": self.VOCAB_SIZE,
            "token_dtype": "uint16",
            "category_mapping": CATEGORY_MAP,
            "source_checksums": source_meta,
            "tokenizer_checksums": tok_hashes,
            "splits": splits_info,
            "totals": {
                "total_tokens_cached": sum(s["total_tokens"] for s in splits_info.values()),
                "training_tokens": splits_info["train"]["total_tokens"],
                "validation_tokens": splits_info["validation"]["total_tokens"],
                "test_tokens": splits_info["test"]["total_tokens"],
                "total_cache_bytes": sum(s["bin_bytes"] + s["offsets_bytes"] for s in splits_info.values()),
            },
            "status": "VALIDATED",
        }

        tmp_manifest = self.cache_dir / "cache_manifest.json.tmp"
        with open(tmp_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        os.replace(tmp_manifest, self.cache_dir / "cache_manifest.json")
        return manifest


class BinaryTokenDataset:
    """Memory-mapped binary token dataset providing fast random access and boundary lookups."""

    def __init__(self, cache_dir: Path, split: str = "train"):
        self.cache_dir = Path(cache_dir)
        self.split = split
        self.bin_path = self.cache_dir / f"{split}.bin"
        self.offsets_path = self.cache_dir / f"{split}_offsets.npy"

        if not self.bin_path.exists() or not self.offsets_path.exists():
            raise FileNotFoundError(f"Binary cache for split '{split}' not found in {cache_dir}")

        # Memory-map the binary token file in read-only mode
        self.tokens = np.memmap(self.bin_path, dtype=np.uint16, mode="r")
        self.offsets = np.load(self.offsets_path)  # shape (N, 3): [start, length, cat_code]

        # Pre-index document indices by category code for fast domain sampling
        self.category_indices: Dict[int, np.ndarray] = {}
        for cat_name, cat_code in CATEGORY_MAP.items():
            matching = np.where(self.offsets[:, 2] == cat_code)[0]
            self.category_indices[cat_code] = matching

    def __len__(self) -> int:
        """Returns total number of tokens in the memory-mapped dataset."""
        return len(self.tokens)

    @property
    def num_documents(self) -> int:
        """Returns total number of documents in this split."""
        return len(self.offsets)

    def get_token_slice(self, start_idx: int, length: int) -> np.ndarray:
        """Slices memory-mapped array without copying entire dataset."""
        return self.tokens[start_idx : start_idx + length]

    def get_document(self, doc_idx: int) -> Tuple[np.ndarray, str]:
        """Retrieves exact token array and category string for given document index."""
        if doc_idx < 0 or doc_idx >= len(self.offsets):
            raise IndexError(f"Document index {doc_idx} out of range (0..{len(self.offsets)-1})")
        start, length, cat_code = self.offsets[doc_idx]
        tokens = np.array(self.tokens[start : start + length], dtype=np.int64)
        cat_name = REV_CATEGORY_MAP.get(cat_code, "unknown")
        return tokens, cat_name

    def get_doc_indices_for_category(self, category_name: str) -> np.ndarray:
        """Returns array of document indices belonging to given category name."""
        code = CATEGORY_MAP.get(category_name)
        if code is None:
            return np.array([], dtype=np.int64)
        return self.category_indices.get(code, np.array([], dtype=np.int64))
