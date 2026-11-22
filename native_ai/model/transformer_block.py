"""Transformer Block for LOVE Native AI.

Combines RMSNorm, CausalSelfAttention, and SwiGLUFeedForward with
pre-normalization residual connections.
"""
from typing import Optional
import torch
import torch.nn as nn
from native_ai.model.normalization import RMSNorm
from native_ai.model.attention import CausalSelfAttention
from native_ai.model.feedforward import SwiGLUFeedForward

class TransformerBlock(nn.Module):
    def __init__(
        self,
        hidden_dim: int,
        n_heads: int,
        head_dim: int,
        ffn_dim: int,
        max_seq_len: int = 512,
        norm_eps: float = 1e-5,
        rope_base: float = 10000.0,
        dropout: float = 0.0,
    ):
        super().__init__()
        self.attn_norm = RMSNorm(hidden_dim, eps=norm_eps)
        self.attn = CausalSelfAttention(
            hidden_dim=hidden_dim,
            n_heads=n_heads,
            head_dim=head_dim,
            max_seq_len=max_seq_len,
            rope_base=rope_base,
            dropout=dropout,
        )
        self.ffn_norm = RMSNorm(hidden_dim, eps=norm_eps)
        self.ffn = SwiGLUFeedForward(hidden_dim=hidden_dim, ffn_dim=ffn_dim)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        use_sdpa: bool = True,
    ) -> torch.Tensor:
        # Pre-norm residual connection for attention
        x = x + self.attn(self.attn_norm(x), attention_mask=attention_mask, use_sdpa=use_sdpa)
        # Pre-norm residual connection for FFN
        x = x + self.ffn(self.ffn_norm(x))
        return x
