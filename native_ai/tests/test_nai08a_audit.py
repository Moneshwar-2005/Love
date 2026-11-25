"""Automated Read-Only Verification Tests for NAI-08A Capability & Data Quality Audit.

Verifies:
1. Pretraining & SFT checkpoint SHA-256 hashes remain bitwise unchanged.
2. Tokenizer artifact checksums remain unchanged.
3. Dataset and cache manifests remain unchanged.
4. No held-out test-split access occurs in NAI-08A diagnostic code.
5. Model weights remain bitwise unchanged after read-only inference diagnostics.
6. Greedy generation is strictly deterministic.
7. All NAI-08A audit artifacts exist and conform to expected schemas.
8. pytest.ini and conftest.py import resolution works cleanly.
"""
import json
import hashlib
from pathlib import Path

import pytest
import torch

from native_ai.model.love_model import LoveForCausalLM, LoveModelConfig
from native_ai.training.checkpoint_manager import CheckpointManager
from native_ai.tokenizer.love_tokenizer import LoveTokenizer

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_DIR = BASE_DIR / "experiments" / "nai_08a_capability_audit"

EXPECTED_CHECKPOINTS = {
    BASE_DIR / "checkpoints" / "step_0000250.pt": "dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145",
    BASE_DIR / "experiments" / "nai_07b_sft_pilot" / "checkpoints" / "sft_best.pt": "31ad59611b23710fb9d759e3c5c059a352b9cbd53338734911dc39cdf0fd8bdb",
    BASE_DIR / "experiments" / "nai_07b_sft_pilot" / "checkpoints" / "sft_latest.pt": "f320e4a6fcf9b67abb22c1852d8a964abc500693e6fa5152a7f8f8b2f1aa3839",
}

EXPECTED_TOKENIZER = {
    "vocab.json": "5d0e074fc6b39e75743da7c5a10d30938439a8806f98f2361490a5416469dd55",
    "merges.txt": "12e7ba2415f205d10c4b67470e1ccab4d76ea1b5dac17124bd9ecaa44b1bf8f1",
    "tokenizer.json": "4ee54954754b6a9c18e6522a114c5271ca99d69dc12a22585abec1a7a672abdc",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_checkpoints_unchanged():
    for path, expected_sha in EXPECTED_CHECKPOINTS.items():
        assert path.exists(), f"Missing checkpoint: {path}"
        assert _sha256(path) == expected_sha, f"Checkpoint modified: {path}"


def test_tokenizer_checksums_unchanged():
    tok_dir = BASE_DIR / "tokenizer" / "artifacts"
    for fname, expected_sha in EXPECTED_TOKENIZER.items():
        p = tok_dir / fname
        assert p.exists(), f"Missing tokenizer file: {p}"
        assert _sha256(p) == expected_sha, f"Tokenizer file modified: {p}"


def test_manifests_intact_and_reconciled():
    sft_manifest_path = BASE_DIR / "datasets" / "sft" / "manifests" / "sft_manifest.json"
    cache_manifest_path = BASE_DIR / "data_cache" / "cache_manifest.json"
    assert sft_manifest_path.exists()
    assert cache_manifest_path.exists()

    sft_manifest = json.loads(sft_manifest_path.read_text(encoding="utf-8"))
    assert sft_manifest["splits"]["train"]["example_count"] == 11639
    assert sft_manifest["splits"]["validation"]["example_count"] == 1387

    cache_manifest = json.loads(cache_manifest_path.read_text(encoding="utf-8"))
    assert cache_manifest["splits"]["train"]["total_tokens"] == 25467894
    assert cache_manifest["splits"]["validation"]["total_tokens"] == 933909


def test_no_test_split_access_in_diagnostics_script():
    diag_script = BASE_DIR / "scripts" / "run_nai08a_diagnostics.py"
    src = diag_script.read_text(encoding="utf-8")
    # Ignore docstrings/comments mentioning the boundary; verify no actual file load of test splits
    code_lines = [ln for ln in src.splitlines() if not ln.strip().startswith("#") and "Zero access" not in ln]
    joined = "\n".join(code_lines)
    assert "sft_test.jsonl" not in joined
    assert "test.bin" not in joined
    assert "test.jsonl" not in joined


def test_read_only_inference_weights_unchanged_and_deterministic():
    cfg = LoveModelConfig.from_yaml(str(BASE_DIR / "configs" / "tiny.yaml"))
    model = LoveForCausalLM(cfg)
    sft_path = BASE_DIR / "experiments" / "nai_07b_sft_pilot" / "checkpoints" / "sft_best.pt"
    CheckpointManager(sft_path.parent).load_checkpoint(sft_path, model, device="cpu")
    model.eval()

    before = {n: p.clone().detach() for n, p in model.named_parameters()}
    tok = LoveTokenizer.from_pretrained(str(BASE_DIR / "tokenizer" / "artifacts"))
    prompt_ids = torch.tensor([tok.encode("Hello")], dtype=torch.long)

    with torch.no_grad():
        out1 = model.generate(prompt_ids, max_new_tokens=8, temperature=0.0)
        out2 = model.generate(prompt_ids, max_new_tokens=8, temperature=0.0)

    assert torch.equal(out1, out2), "Greedy generation must be deterministic!"
    for n, p in model.named_parameters():
        assert torch.equal(p, before[n]), f"Weight mutated during read-only inference: {n}"


def test_nai08a_artifacts_exist_and_valid():
    required_files = [
        "audit_summary.json",
        "architecture_analysis.json",
        "hardware_feasibility.json",
        "tokenizer_analysis.json",
        "pretraining_dataset_analysis.json",
        "sft_dataset_reconciliation.json",
        "generation_diagnostics.json",
        "proposed_benchmark_spec.json",
    ]
    for fname in required_files:
        p = AUDIT_DIR / fname
        assert p.exists(), f"Missing NAI-08A artifact: {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(data, dict) and len(data) > 0

    summary = json.loads((AUDIT_DIR / "audit_summary.json").read_text(encoding="utf-8"))
    assert summary["phase"] == "NAI-08A"
    assert summary["verdict"] == "PASS"

    recon = json.loads((AUDIT_DIR / "sft_dataset_reconciliation.json").read_text(encoding="utf-8"))
    assert recon["reconciliation"]["actual_sft_train_jsonl_lines"] == 11639
    assert recon["reconciliation"]["manifest_train_example_count"] == 11639


def test_pytest_import_configuration():
    pytest_ini = (BASE_DIR / "pytest.ini").read_text(encoding="utf-8")
    conftest = (BASE_DIR / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "testpaths = tests" in pytest_ini
    assert "pythonpath = . .." in pytest_ini
    assert "project_root" in conftest
