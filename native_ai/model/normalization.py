"""Root Mean Square Layer Normalization (RMSNorm) for LOVE Native AI.

Implements numerically stable RMSNorm as described in Zhang & Sennrich (2019).
Calculates RMS in float32 for stability even when inputs are in lower precision.
"""
import torch
import torch.nn as nn

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        # Compute RMS in float32 for numerical stability
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self._norm(x.float()).type_as(x)
        return output * self.weight
