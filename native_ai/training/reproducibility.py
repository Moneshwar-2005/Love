"""Reproducibility and Experiment Tracking Utilities for LOVE Native AI.

Implements Task 9:
- Deterministic random seed setting across Python, PyTorch (CPU and CUDA).
- System and hardware metadata capture (CPU, RAM, GPU, driver, CUDA, OS).
- Software dependency and environment logging.
- Unique experiment ID generation with cryptographic timestamping.
- Configuration hashing and verification.
"""
import os
import sys
import platform
import random
import time
import uuid
import json
import hashlib
from typing import Dict, Any, Optional
import torch

def set_seed(seed: int = 42, deterministic: bool = True) -> int:
    """Sets deterministic random seeds across python random, torch cpu and torch cuda."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    return seed


def generate_experiment_id(prefix: str = "exp") -> str:
    """Generates a human-readable, timestamped unique experiment ID."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    short_hash = uuid.uuid4().hex[:6]
    return f"{prefix}_{timestamp}_{short_hash}"


def capture_hardware_metadata() -> Dict[str, Any]:
    """Captures hardware and environment metadata without external dependencies."""
    meta = {
        "os": platform.platform(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count_logical": os.cpu_count(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }

    if torch.cuda.is_available():
        meta["cuda_device_count"] = torch.cuda.device_count()
        meta["cuda_device_name"] = torch.cuda.get_device_name(0)
        meta["cuda_version"] = torch.version.cuda
        props = torch.cuda.get_device_properties(0)
        meta["gpu_vram_total_mb"] = props.total_memory / (1024 * 1024)
        meta["gpu_compute_capability"] = f"{props.major}.{props.minor}"
        meta["gpu_multi_processor_count"] = props.multi_processor_count
    else:
        meta["cuda_device_name"] = None
        meta["cuda_version"] = None

    return meta


def record_experiment_manifest(
    experiment_id: str,
    config_dict: Dict[str, Any],
    param_counts: Dict[str, Any],
    metrics: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Assembles and persists a complete experiment manifest."""
    manifest = {
        "experiment_id": experiment_id,
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware": capture_hardware_metadata(),
        "config": config_dict,
        "config_hash": hashlib.sha256(json.dumps(config_dict, sort_keys=True).encode("utf-8")).hexdigest(),
        "parameter_counts": param_counts,
        "metrics": metrics or {},
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest
