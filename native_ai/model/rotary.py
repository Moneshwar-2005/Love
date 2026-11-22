"""Rotary Position Embedding (RoPE) implementation for LOVE Native AI.

Implements RoPE (Su et al., 2021) to inject positional awareness into
queries and keys in multi-head self-attention.
"""
import torch
import torch.nn as nn
from typing import Tuple

class RotaryEmbedding(nn.Module):
    """Precomputes and applies Rotary Position Embeddings (RoPE)."""
    def __init__(self, dim: int, max_seq_len: int = 512, base: float = 10000.0):
        super().__init__()
        assert dim % 2 == 0, f"Rotary embedding dimension must be even, got {dim}"
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base
        # Precompute inv_freq: theta_i = base^(-2*(i-1)/dim)
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self._build_cos_sin_cache(max_seq_len)

    def _build_cos_sin_cache(self, max_seq_len: int, device=None, dtype=None):
        self.max_seq_len = max_seq_len
        t = torch.arange(max_seq_len, device=device or self.inv_freq.device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)  # [seq_len, dim // 2]
        emb = torch.cat((freqs, freqs), dim=-1)  # [seq_len, dim]
        self.register_buffer("cos_cached", emb.cos(), persistent=False)
        self.register_buffer("sin_cached", emb.sin(), persistent=False)

    def forward(self, x: torch.Tensor, seq_len: int) -> Tuple[torch.Tensor, torch.Tensor]:
        if seq_len > self.max_seq_len:
            self._build_cos_sin_cache(seq_len, device=x.device, dtype=x.dtype)
        cos = self.cos_cached[:seq_len].to(dtype=x.dtype, device=x.device)
        sin = self.sin_cached[:seq_len].to(dtype=x.dtype, device=x.device)
        return cos, sin

def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """Rotates half the hidden dimensions of the input."""
    half = x.shape[-1] // 2
    x1 = x[..., :half]
    x2 = x[..., half:]
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb(q: torch.Tensor, k: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Applies RoPE to queries and keys.
    q, k: [batch, n_heads, seq_len, head_dim]
    cos, sin: [seq_len, head_dim]
    """
    cos = cos.unsqueeze(0).unsqueeze(1)  # [1, 1, seq_len, head_dim]
    sin = sin.unsqueeze(0).unsqueeze(1)  # [1, 1, seq_len, head_dim]
    q_embed = (q * cos) + (rotate_half(q) * sin)
    k_embed = (k * cos) + (rotate_half(k) * sin)
    return q_embed, k_embed
