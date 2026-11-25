"""Dataset Source Registry and Provenance Tracker for LOVE Native AI.

Implements Task 5 (NAI-03) & Task 1 (NAI-03.1):
- Maintains formal registry of all ingested data sources
- Records: source name, origin/location, license, license reference, permitted usage,
  restrictions, file checksums, retrieval/processing timestamps, and category assignment.
- Strictly validates source provenance:
  - Exact creator or origin
  - Source type: original synthetic vs externally sourced
  - Applicable license and license evidence supporting designation
  - Flags uncertain license records as UNRESOLVED and excludes them from approved training corpora
- Strictly validates that all approved sources hold explicit CC0, Public Domain, or verified permissive licenses.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
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
    creator: str = "LOVE Native AI Project / curate_raw_sources.py"
    source_type: str = "original_synthetic"  # "original_synthetic" or "external"
    license_status: str = "VERIFIED"  # "VERIFIED", "UNRESOLVED", "PENDING_REVIEW"
    license_evidence: str = "Direct project creation; dedicated for training"
    is_approved_for_training: bool = True
    dataset_revision: Optional[str] = None
    license_file_path: Optional[str] = None
    license_file_sha256: Optional[str] = None
    attribution_requirements: Optional[str] = None
    processing_version: str = "1.0.0"
    approval_status: str = "APPROVED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetSourceRegistry:
    """Registry maintaining provenance and legal compliance for all datasets."""

    APPROVED_LICENSES = {
        "CC0-1.0", "Public Domain", "MIT", "Apache-2.0", "CC-BY-4.0", "BSD-3-Clause", "CDLA-Permissive-2.0", "CDLA-Sharing-1.0"
    }

    CATEGORIES = {
        "general_english": "A. General English and Knowledge",
        "reasoning_math": "B. Reasoning and Mathematics",
        "instruction_dialog": "C. Instructions and Conversations",
        "technical_code": "D. Coding and Technical Material",
        "structured_tasks": "E. Other Structured Tasks",
        "english_synthetic_stories": "F. English Synthetic Stories",
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
                restrictions="None. Dedicated to public domain by author.",
                retrieval_date=now,
                processing_date=now,
                creator="LOVE Native AI Project / curate_raw_sources.py",
                source_type="original_synthetic",
                license_status="VERIFIED",
                license_evidence="Authored directly within curate_raw_sources.py by project author and dedicated to Public Domain (CC0-1.0).",
                is_approved_for_training=True,
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
                creator="LOVE Native AI Project / curate_raw_sources.py",
                source_type="original_synthetic",
                license_status="VERIFIED",
                license_evidence="Authored directly within curate_raw_sources.py by project author and dedicated to Public Domain (CC0-1.0).",
                is_approved_for_training=True,
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
                creator="LOVE Native AI Project / curate_raw_sources.py",
                source_type="original_synthetic",
                license_status="VERIFIED",
                license_evidence="Authored directly within curate_raw_sources.py by project author and dedicated to Public Domain (CC0-1.0).",
                is_approved_for_training=True,
            ),
            DatasetSourceRecord(
                source_id="src_tech_01",
                source_name="LOVE Computer Science, Software Engineering & Systems Corpus",
                category="technical_code",
                origin_location="native_ai/datasets/raw/technical_code.jsonl",
                license_type="MIT",
                license_reference="https://opensource.org/licenses/MIT",
                permitted_usage="Commercial and non-commercial model training, redistribution of derivative weights",
                restrictions="Uncertain provenance: text is internal synthetic fixture, not an external MIT release.",
                retrieval_date=now,
                processing_date=now,
                creator="LOVE Native AI Project / curate_raw_sources.py",
                source_type="original_synthetic",
                license_status="UNRESOLVED",
                license_evidence="UNRESOLVED: Previously labeled 'MIT' without third-party copyright deed or upstream repository. Text was authored synthetically in-project. Excluded from approved training corpus pending re-licensing as CC0 or project-internal dedication.",
                is_approved_for_training=False,
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
                creator="LOVE Native AI Project / curate_raw_sources.py",
                source_type="original_synthetic",
                license_status="VERIFIED",
                license_evidence="Authored directly within curate_raw_sources.py by project author and dedicated to Public Domain (CC0-1.0).",
                is_approved_for_training=True,
            ),
            DatasetSourceRecord(
                source_id="src_ext_gsm8k",
                source_name="GSM8K (Grade School Math 8K)",
                category="reasoning_math",
                origin_location="native_ai/datasets/raw/external/gsm8k/train.parquet",
                license_type="MIT",
                license_reference="https://opensource.org/licenses/MIT",
                permitted_usage="Commercial and non-commercial model training, evaluation and derivative weights release",
                restrictions="Preserve copyright and license notice in source registry metadata.",
                retrieval_date=now,
                processing_date=now,
                creator="Cobbe et al., OpenAI",
                source_type="external",
                license_status="VERIFIED",
                license_evidence="Official OpenAI GSM8K repository declaring MIT license (arXiv:2110.14168).",
                is_approved_for_training=True,
                dataset_revision="740312add88f781978c0658806c59bc2815b9866",
                license_file_path="native_ai/datasets/raw/external/gsm8k/README.md",
                license_file_sha256="a17e882503578c9e324560630e31017617714ee025c87cf4fea6fd916895f3c1",
                attribution_requirements="Cobbe et al. (OpenAI), 'Training Verifiers to Solve Math Word Problems' (2021)",
                approval_status="APPROVED",
            ),
            DatasetSourceRecord(
                source_id="src_ext_oasst1",
                source_name="OpenAssistant Conversations (OASST1 - English Filtered)",
                category="instruction_dialog",
                origin_location="native_ai/datasets/raw/external/oasst1/train.parquet",
                license_type="Apache-2.0",
                license_reference="https://www.apache.org/licenses/LICENSE-2.0",
                permitted_usage="Unrestricted model pretraining, fine-tuning, and weights redistribution",
                restrictions="Comply with Apache-2.0 terms, preserve copyright and attribution notices.",
                retrieval_date=now,
                processing_date=now,
                creator="OpenAssistant Contributors, LAION AI",
                source_type="external",
                license_status="VERIFIED",
                license_evidence="Official OpenAssistant repository with formal Apache-2.0 LICENSE file.",
                is_approved_for_training=True,
                dataset_revision="fdf72ae0827c1cda404aff25b6603abec9e3399b",
                license_file_path="native_ai/datasets/raw/external/oasst1/LICENSE",
                license_file_sha256="c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
                attribution_requirements="OpenAssistant Contributors, LAION AI (2023)",
                approval_status="APPROVED",
            ),
            DatasetSourceRecord(
                source_id="src_ext_tinystories",
                source_name="TinyStories (Synthetic English Narrative Reasoning)",
                category="english_synthetic_stories",
                origin_location="native_ai/datasets/raw/external/tinystories/train_shard0.parquet",
                license_type="CDLA-Sharing-1.0",
                license_reference="https://cdla.dev/sharing-1-0/",
                permitted_usage="Model pretraining and synthetic reasoning representation learning",
                restrictions="CDLA-Sharing-1.0: Derived data must be made available under CDLA-Sharing-1.0. Model checkpoints remain internal until distribution rights review.",
                retrieval_date=now,
                processing_date=now,
                creator="Ronen Eldan & Yuanzhi Li, Microsoft Research",
                source_type="external",
                license_status="VERIFIED",
                license_evidence="Official TinyStories repository declaring CDLA-Sharing-1.0; official license notice preserved.",
                is_approved_for_training=True,
                dataset_revision="f54c09fd23315a6f9c86f9dc80f725de7d8f9c64",
                license_file_path="native_ai/datasets/raw/external/tinystories/LICENSE",
                license_file_sha256="e0c9a1e7ce2911d829db9c848db9c1501d4618e3094dbee125ef35ac0ece08ba",
                attribution_requirements="Ronen Eldan and Yuanzhi Li (Microsoft Research), 'TinyStories' (2023)",
                approval_status="APPROVED",
            ),
        ]

        for r in records:
            self.register_source(r)

    def register_source(self, record: DatasetSourceRecord) -> None:
        """Registers a new source, enforcing category, license validity, and provenance."""
        if record.category not in self.CATEGORIES:
            raise ValueError(f"Invalid category '{record.category}'. Must be one of: {list(self.CATEGORIES.keys())}")
        if record.license_type not in self.APPROVED_LICENSES:
            raise ValueError(f"License '{record.license_type}' is not approved for training. Approved: {self.APPROVED_LICENSES}")

        # Enforce consistency: if license status is not VERIFIED, cannot approve for training
        if record.license_status != "VERIFIED":
            record.is_approved_for_training = False

        self.sources[record.source_id] = record

    @classmethod
    def validate_source_provenance(cls, record: DatasetSourceRecord) -> Tuple[bool, List[str]]:
        """Strictly validates source provenance and license evidence completeness."""
        issues: List[str] = []
        if not record.creator or not record.creator.strip():
            issues.append("Missing creator attribution")
        if record.source_type not in {"original_synthetic", "external"}:
            issues.append(f"Invalid source_type '{record.source_type}' (must be 'original_synthetic' or 'external')")
        if not record.license_evidence or len(record.license_evidence.strip()) < 15:
            issues.append("Missing or insufficient license evidence supporting designation")
        if record.license_status not in {"VERIFIED", "UNRESOLVED", "PENDING_REVIEW"}:
            issues.append(f"Invalid license_status '{record.license_status}'")
        if record.license_status != "VERIFIED" and record.is_approved_for_training:
            issues.append("Source with unverified/unresolved license cannot be approved for training")
        if record.license_type not in cls.APPROVED_LICENSES:
            issues.append(f"License '{record.license_type}' is not approved")
        return len(issues) == 0, issues

    def get_approved_sources(self) -> Dict[str, DatasetSourceRecord]:
        """Returns only sources with verified license and approved training status."""
        return {
            k: v for k, v in self.sources.items()
            if v.is_approved_for_training and v.license_status == "VERIFIED"
        }

    def get_unresolved_sources(self) -> Dict[str, DatasetSourceRecord]:
        """Returns sources flagged as unresolved or not approved for training."""
        return {
            k: v for k, v in self.sources.items()
            if not v.is_approved_for_training or v.license_status != "VERIFIED"
        }

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
        """Saves registry to JSON file with full provenance and approval status."""
        target = out_path or (MANIFESTS_DIR / "source_registry.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        approved_count = len(self.get_approved_sources())
        unresolved_count = len(self.get_unresolved_sources())
        data = {
            "version": "1.1.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_sources": len(self.sources),
            "approved_sources_count": approved_count,
            "unresolved_sources_count": unresolved_count,
            "sources": {k: v.to_dict() for k, v in self.sources.items()}
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data


if __name__ == "__main__":
    reg = DatasetSourceRegistry()
    exported = reg.export_registry()
    print(f"Dataset Source Registry updated with {exported['total_sources']} sources "
          f"({exported['approved_sources_count']} approved, {exported['unresolved_sources_count']} unresolved).")
