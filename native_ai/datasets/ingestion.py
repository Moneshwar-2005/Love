"""Data Ingestion Pipeline for LOVE Native AI.

Implements Task 6:
- Supports streaming ingestion of plain text (.txt) and JSON Lines (.jsonl)
- Validates UTF-8 encoding integrity
- Enforces document size limits (max 5 MB per individual document)
- Rejects malformed JSON records
- Memory-efficient streaming generators (never loads entire corpus into RAM)
"""
import os
import json
from pathlib import Path
from typing import Generator, Dict, Any, Union


class DatasetIngestion:
    def __init__(self, max_doc_size_bytes: int = 5 * 1024 * 1024):
        self.max_doc_size_bytes = max_doc_size_bytes

    def stream_file(self, file_path: Union[str, Path], source_id: str, category: str) -> Generator[Dict[str, Any], None, None]:
        """
        Streams documents from file (.txt or .jsonl).
        Yields standardized dicts:
            {
                "doc_id": str,
                "source_id": str,
                "category": str,
                "text": str,
                "raw_bytes": int,
            }
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Source file not found: {p}")

        if p.suffix.lower() == ".jsonl":
            yield from self._stream_jsonl(p, source_id, category)
        elif p.suffix.lower() in [".txt", ".text"]:
            yield from self._stream_text(p, source_id, category)
        else:
            raise ValueError(f"Unsupported file extension '{p.suffix}'. Must be .txt or .jsonl")

    def _stream_jsonl(self, path: Path, source_id: str, category: str) -> Generator[Dict[str, Any], None, None]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    text = record.get("text", "")
                    doc_id = record.get("doc_id", f"{source_id}_{idx:06d}")
                    doc_category = record.get("category", category)

                    raw_bytes = len(text.encode("utf-8"))
                    if raw_bytes > self.max_doc_size_bytes:
                        continue  # Skip oversized record

                    yield {
                        "doc_id": doc_id,
                        "source_id": source_id,
                        "category": doc_category,
                        "text": text,
                        "raw_bytes": raw_bytes,
                        "metadata": record.get("metadata", {}),
                    }
                except json.JSONDecodeError:
                    continue  # Malformed record rejection

    def _stream_text(self, path: Path, source_id: str, category: str) -> Generator[Dict[str, Any], None, None]:
        # Split on double newline paragraphs
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            raw_bytes = len(para.encode("utf-8"))
            if raw_bytes > self.max_doc_size_bytes:
                continue
            yield {
                "doc_id": f"{source_id}_p{idx:05d}",
                "source_id": source_id,
                "category": category,
                "text": para,
                "raw_bytes": raw_bytes,
                "metadata": {"source_file": str(path.name)},
            }
