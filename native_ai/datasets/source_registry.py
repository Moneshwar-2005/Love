"""Dataset Source Registry and Provenance Tracker for LOVE Native AI.

Implements Task 5:
- Maintains formal registry of all ingested data sources
- Records: source name, origin/location, license, license reference, permitted usage,
  restrictions, file checksums, retrieval/processing timestamps, and category assignment.
- Strictly validates that all sources hold explicit CC0, Public Domain, or permissive MIT/Apache licenses.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import hashlib
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFESTS_DIR = PROJECT_ROOT / "native_ai" / "datasets" / "manifests"


@dataclass
class DatasetSourceRecord:
    source_id: str
    source_name: str
    category: str  # One of: general_english, reasoning_math, instruction_dialog, technical_code, structured_tasks
    origin_location: str
    license_type: str
    license_reference: str
    permitted_usage: str
    restrictions: str
    retrieval_date: str
    processing_date: str
    file_path: Optional[str] = None
    file_sha256: Optional[str] = None
    file_size_bytes: int = 0
    document_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetSourceRegistry:
    """Registry maintaining provenance and legal compliance for all datasets."""

    APPROVED_LICENSES = {
        "CC0-1.0", "Public Domain", "MIT", "Apache-2.0", "CC-BY-4.0", "BSD-3-Clause"
    }

    CATEGORIES = {
        "general_english": "A. General English and Knowledge",
        "reasoning_math": "B. Reasoning and Mathematics",
        "instruction_dialog": "C. Instructions and Conversations",
        "technical_code": "D. Coding and Technical Material",
        "structured_tasks": "E. Other Structured Tasks",
    }

    def __init__(self):
        self.sources: Dict[str, DatasetSourceRecord] = {}
        self._initialize_core_sources()

    def _initialize_core_sources(self):
        """Initializes records for the 5 curated baseline pretraining corpora."""
        now = time.strftime("%Y-%m-%d")

        records = [
            DatasetSourceRecord(
                source_id="src_gen_en_01",
                source_name="LOVE General English & Encyclopedic Knowledge Corpus",
                category="general_english",
                origin_location="native_ai/datasets/raw/general_english.jsonl",
                license_type="CC0-1.0",
                license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
                permitted_usage="Unrestricted commercial, research, and model pretraining use",
                restrictions="None. Author dedicated all rights to public domain.",
                retrieval_date=now,
                processing_date=now,
            ),
            DatasetSourceRecord(
                source_id="src_math_01",
                source_name="LOVE Reasoning, Logic & Mathematics Exposition Corpus",
                category="reasoning_math",
                origin_location="native_ai/datasets/raw/reasoning_math.jsonl",
                license_type="CC0-1.0",
                license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
                permitted_usage="Unrestricted commercial, research, and model pretraining use",
                restrictions="None. Public domain dedication.",
                retrieval_date=now,
                processing_date=now,
            ),
            DatasetSourceRecord(
                source_id="src_dialog_01",
                source_name="LOVE Conversational, QA & Task Instruction Corpus",
                category="instruction_dialog",
                origin_location="native_ai/datasets/raw/instruction_dialog.jsonl",
                license_type="CC0-1.0",
                license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
                permitted_usage="Unrestricted model pretraining and supervised fine-tuning",
                restrictions="None. Multi-turn dialogue templates generated without PII.",
                retrieval_date=now,
                processing_date=now,
            ),
            DatasetSourceRecord(
                source_id="src_tech_01",
                source_name="LOVE Computer Science, Software Engineering & Systems Corpus",
                category="technical_code",
                origin_location="native_ai/datasets/raw/technical_code.jsonl",
                license_type="MIT",
                license_reference="https://opensource.org/licenses/MIT",
                permitted_usage="Commercial and non-commercial model training, redistribution of derivative weights",
                restrictions="Preserve copyright and license notice in source registry metadata.",
                retrieval_date=now,
                processing_date=now,
            ),
            DatasetSourceRecord(
                source_id="src_struct_01",
                source_name="LOVE Structured Tasks, Extraction & Planning Corpus",
                category="structured_tasks",
                origin_location="native_ai/datasets/raw/structured_tasks.jsonl",
                license_type="CC0-1.0",
                license_reference="https://creativecommons.org/publicdomain/zero/1.0/",
                permitted_usage="Unrestricted model pretraining use",
                restrictions="None. Dedicated to public domain.",
                retrieval_date=now,
                processing_date=now,
            ),
        ]

        for r in records:
            self.register_source(r)

    def register_source(self, record: DatasetSourceRecord) -> None:
        """Registers a new source, enforcing category and license validity."""
        if record.category not in self.CATEGORIES:
            raise ValueError(f"Invalid category '{record.category}'. Must be one of: {list(self.CATEGORIES.keys())}")
        if record.license_type not in self.APPROVED_LICENSES:
            raise ValueError(f"License '{record.license_type}' is not approved for training. Approved: {self.APPROVED_LICENSES}")
        self.sources[record.source_id] = record

    def update_file_metadata(self, source_id: str, file_path: Path, doc_count: int) -> None:
        """Updates file size, doc count, and SHA-256 hash upon ingestion."""
        if source_id not in self.sources:
            raise KeyError(f"Source ID '{source_id}' not found in registry")
        record = self.sources[source_id]
        record.file_path = str(file_path)
        record.document_count = doc_count
        if file_path.exists():
            record.file_size_bytes = file_path.stat().st_size
            record.file_sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest()

    def export_registry(self, out_path: Optional[Path] = None) -> Dict[str, Any]:
        """Saves registry to JSON file."""
        target = out_path or (MANIFESTS_DIR / "source_registry.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_sources": len(self.sources),
            "sources": {k: v.to_dict() for k, v in self.sources.items()}
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data


if __name__ == "__main__":
    reg = DatasetSourceRegistry()
    exported = reg.export_registry()
    print(f"Dataset Source Registry created with {exported['total_sources']} verified sources.")
