"""Corpus Scale Targets and Hardware Feasibility Modeling for LOVE Native AI.

Implements Task 3:
Evaluates pretraining corpus requirements for the 5.5M-parameter LOVE Transformer:
- Scenario A: Minimal Engineering Pilot (1M tokens)
- Scenario B: Small-Model Experimental Pretraining (20M tokens)
- Scenario C: Expanded Future Training Corpus (100M tokens)

Models storage consumption, processing time, hardware throughput, and memory limits
on the NVIDIA GeForce GTX 1650 (4 GB VRAM) and Intel Core i7-7700 host.
"""
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DRIVE = "F:\\"


@dataclass
class CorpusScaleScenario:
    scenario_id: str
    scenario_name: str
    target_tokens: int
    estimated_documents: int
    avg_tokens_per_doc: int
    raw_text_bytes: int
    processed_jsonl_bytes: int
    tokenized_binary_bytes: int
    total_estimated_disk_bytes: int
    data_processing_time_seconds: float
    gtx_1650_throughput_tokens_sec: float
    epochs_planned: int
    training_time_seconds: float
    peak_vram_mb: float
    hardware_feasibility_status: str  # "FEASIBLE", "MARGINAL", "INVIABLE"
    disk_safety_status: str  # "SAFE", "WARNING_LOW_DISK", "EXCEEDED"
    primary_objective: str
    expected_limitations: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["training_time_minutes"] = round(self.training_time_seconds / 60.0, 2)
        d["training_time_hours"] = round(self.training_time_seconds / 3600.0, 2)
        d["total_disk_mb"] = round(self.total_estimated_disk_bytes / (1024 * 1024), 2)
        d["total_disk_gb"] = round(self.total_estimated_disk_bytes / (1024 * 1024 * 1024), 3)
        return d


def get_disk_free_bytes(path: str = WORKSPACE_DRIVE) -> int:
    """Returns available free disk space in bytes for the target drive."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free
    except Exception:
        # Fallback to conservative estimate if drive inspection fails
        return int(4.5 * 1024 * 1024 * 1024)


def compute_scenario(
    scenario_id: str,
    name: str,
    target_tokens: int,
    avg_tokens_per_doc: int = 250,
    bytes_per_token_raw: float = 3.6,
    jsonl_overhead_ratio: float = 1.35,
    processing_throughput_docs_sec: float = 1200.0,
    gtx_1650_tokens_sec: float = 20000.0,
    epochs: int = 1,
    peak_vram_mb: float = 358.0,
    objective: str = "",
    limitations: str = "",
    available_disk_bytes: Optional[int] = None,
) -> CorpusScaleScenario:
    """Computes exact empirical projections for a pretraining dataset scenario."""
    if available_disk_bytes is None:
        available_disk_bytes = get_disk_free_bytes(WORKSPACE_DRIVE)

    est_docs = int(round(target_tokens / avg_tokens_per_doc))
    raw_bytes = int(round(target_tokens * bytes_per_token_raw))
    processed_bytes = int(round(raw_bytes * jsonl_overhead_ratio))
    # uint16 token IDs require exactly 2 bytes per token
    tokenized_bytes = target_tokens * 2
    total_disk = raw_bytes + processed_bytes + tokenized_bytes

    proc_time = est_docs / max(1.0, processing_throughput_docs_sec)
    total_train_tokens = target_tokens * epochs
    train_time = total_train_tokens / max(1.0, gtx_1650_tokens_sec)

    # Disk safety status
    free_gb = available_disk_bytes / (1024 ** 3)
    used_gb = total_disk / (1024 ** 3)
    if total_disk > available_disk_bytes * 0.70:
        disk_status = "EXCEEDED"
    elif total_disk > available_disk_bytes * 0.40:
        disk_status = "WARNING_LOW_DISK"
    else:
        disk_status = "SAFE"

    # Hardware feasibility
    if peak_vram_mb > 3500.0:
        hw_status = "INVIABLE"
    elif train_time > 86400.0:  # > 24 hours
        hw_status = "MARGINAL"
    else:
        hw_status = "FEASIBLE"

    return CorpusScaleScenario(
        scenario_id=scenario_id,
        scenario_name=name,
        target_tokens=target_tokens,
        estimated_documents=est_docs,
        avg_tokens_per_doc=avg_tokens_per_doc,
        raw_text_bytes=raw_bytes,
        processed_jsonl_bytes=processed_bytes,
        tokenized_binary_bytes=tokenized_bytes,
        total_estimated_disk_bytes=total_disk,
        data_processing_time_seconds=round(proc_time, 2),
        gtx_1650_throughput_tokens_sec=gtx_1650_tokens_sec,
        epochs_planned=epochs,
        training_time_seconds=round(train_time, 2),
        peak_vram_mb=peak_vram_mb,
        hardware_feasibility_status=hw_status,
        disk_safety_status=disk_status,
        primary_objective=objective,
        expected_limitations=limitations,
    )


def get_all_scenarios(available_disk_bytes: Optional[int] = None) -> Dict[str, CorpusScaleScenario]:
    """Generates Scenarios A, B, and C with validated parameters."""
    if available_disk_bytes is None:
        available_disk_bytes = get_disk_free_bytes(WORKSPACE_DRIVE)

    # Scenario A: Minimal Engineering Pilot
    scenario_a = compute_scenario(
        scenario_id="scenario_a_pilot",
        name="A. Minimal Engineering Pilot",
        target_tokens=1_000_000,  # 1M tokens (~1,953 seqs of 512)
        avg_tokens_per_doc=250,
        epochs=3,
        objective="Verify end-to-end training loop, loss convergence, AdamW stability, and checkpointing without memorizing tiny static fixtures.",
        limitations="Cannot learn general world knowledge or deep reasoning; restricted to basic English syntax and token co-occurrence.",
        available_disk_bytes=available_disk_bytes,
    )

    # Scenario B: Small-Model Experimental Pretraining
    scenario_b = compute_scenario(
        scenario_id="scenario_b_pretraining",
        name="B. Small-Model Experimental Pretraining",
        target_tokens=20_000_000,  # 20M tokens (~39,062 seqs of 512, ~3.6 tokens/param)
        avg_tokens_per_doc=280,
        epochs=3,
        objective="Establish functional English language modeling, grammatical coherence, basic arithmetic, and instruction adherence in 5.5M model.",
        limitations="Limited long-tail factual knowledge; restricted by 5.5M parameter representation capacity and 20M token coverage.",
        available_disk_bytes=available_disk_bytes,
    )

    # Scenario C: Expanded Future Training Corpus
    scenario_c = compute_scenario(
        scenario_id="scenario_c_expanded",
        name="C. Expanded Future Training Corpus",
        target_tokens=100_000_000,  # 100M tokens (~195,312 seqs of 512, ~18.2 tokens/param near Chinchilla optimal)
        avg_tokens_per_doc=300,
        epochs=2,
        objective="Fully saturate 5.5M model representation capacity and build foundational multi-domain pretraining corpus for future 15M-30M models.",
        limitations="Consumes ~1.2 GB disk on F: (requires staging discipline); 5.5M architecture capacity will bottleneck before full dataset utility is extracted.",
        available_disk_bytes=available_disk_bytes,
    )

    return {
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "scenario_c": scenario_c,
    }
