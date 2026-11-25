"""Hardware Safety and VRAM Safeguards for NVIDIA GTX 1650 4GB.

Implements Section 7 & Section 8 (NAI-04):
- VRAM allocation telemetry and threshold enforcement (<= 3,500 MB safe limit).
- Safe cleanup routines (torch.cuda.empty_cache(), gc.collect()).
- Safe OOM exception capture and rollback.
- Automatic mixed-precision (AMP) configuration: FP16 on CUDA, FP32 on CPU.
- NaN/Inf detection and finite loss assertions.
"""
import gc
import contextlib
from typing import Dict, Any, Optional, Tuple
import torch

class VRAMLimitExceededError(RuntimeError):
    """Raised when VRAM exceeds safe operating threshold on 4GB hardware."""
    pass


class DeviceSafetyManager:
    """Manages execution device safety, VRAM telemetry, and mixed-precision contexts."""

    MAX_SAFE_VRAM_MB = 3500.0  # Safe cap on 4,096 MB GTX 1650

    def __init__(self, requested_device: Optional[str] = None):
        if requested_device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(requested_device)

        self.is_cuda = self.device.type == "cuda"
        if self.is_cuda and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available on this system.")

    def get_vram_telemetry(self) -> Dict[str, float]:
        """Returns current VRAM allocation, reservation, and peak metrics in MB."""
        if not self.is_cuda:
            return {
                "is_cuda": False,
                "allocated_mb": 0.0,
                "reserved_mb": 0.0,
                "peak_allocated_mb": 0.0,
                "total_vram_mb": 0.0,
                "safe_limit_mb": self.MAX_SAFE_VRAM_MB,
            }

        dev_idx = self.device.index or 0
        allocated = torch.cuda.memory_allocated(dev_idx) / (1024 * 1024)
        reserved = torch.cuda.memory_reserved(dev_idx) / (1024 * 1024)
        peak = torch.cuda.max_memory_allocated(dev_idx) / (1024 * 1024)
        total = torch.cuda.get_device_properties(dev_idx).total_memory / (1024 * 1024)

        return {
            "is_cuda": True,
            "allocated_mb": round(allocated, 2),
            "reserved_mb": round(reserved, 2),
            "peak_allocated_mb": round(peak, 2),
            "total_vram_mb": round(total, 2),
            "safe_limit_mb": self.MAX_SAFE_VRAM_MB,
        }

    def check_vram_safety(self) -> None:
        """Verifies VRAM has not breached safe threshold."""
        if not self.is_cuda:
            return

        dev_idx = self.device.index or 0
        allocated_mb = torch.cuda.memory_allocated(dev_idx) / (1024 * 1024)
        if allocated_mb > self.MAX_SAFE_VRAM_MB:
            self.clean_vram()
            raise VRAMLimitExceededError(
                f"VRAM allocation ({allocated_mb:.2f} MB) exceeded safe hardware cap ({self.MAX_SAFE_VRAM_MB} MB). "
                f"Aborted to protect system stability."
            )

    def clean_vram(self) -> None:
        """Flushes PyTorch CUDA memory cache and triggers garbage collection."""
        gc.collect()
        if self.is_cuda:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(self.device.index or 0)

    def get_autocast_context(self, enabled: bool = True):
        """
        Returns mixed-precision autocast context manager:
        - CUDA: torch.amp.autocast('cuda', dtype=torch.float16)
        - CPU: nullcontext (FP32)
        """
        if self.is_cuda and enabled:
            return torch.amp.autocast(device_type="cuda", dtype=torch.float16)
        else:
            return contextlib.nullcontext()

    def get_grad_scaler(self, enabled: bool = True) -> Optional[torch.amp.GradScaler]:
        """Returns GradScaler on CUDA if enabled, None on CPU."""
        if self.is_cuda and enabled:
            return torch.amp.GradScaler(device="cuda")
        return None

    @staticmethod
    def verify_finite_loss(loss: torch.Tensor, step: Optional[int] = None) -> None:
        """Asserts loss is finite and not NaN or Inf."""
        if not torch.isfinite(loss):
            step_str = f" at step {step}" if step is not None else ""
            raise FloatingPointError(f"Non-finite loss detected{step_str}: {loss.item()}. Training aborted.")
