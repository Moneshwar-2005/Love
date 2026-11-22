"""Causal Multi-Head Self-Attention with RoPE for LOVE Native AI.

Implements causal masking to prevent future-token leakage, integrates
rotary position embeddings, and supports both PyTorch SDPA and explicit
attention matrix computation.
"""
import math
from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from native_ai.model.rotary import RotaryEmbedding, apply_rotary_pos_emb

class CausalSelfAttention(nn.Module):
    def __init__(
        self,
        hidden_dim: int,
        n_heads: int,
        head_dim: int,
        max_seq_len: int = 512,
        rope_base: float = 10000.0,
        dropout: float = 0.0,
    ):
        super().__init__()
        assert hidden_dim == n_heads * head_dim, (
            f"hidden_dim ({hidden_dim}) must equal n_heads ({n_heads}) * head_dim ({head_dim})"
        )
        self.hidden_dim = hidden_dim
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.dropout_rate = dropout

        self.q_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.out_proj = nn.Linear(hidden_dim, hidden_dim, bias=False)

        self.rotary_emb = RotaryEmbedding(dim=head_dim, max_seq_len=max_seq_len, base=rope_base)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        use_sdpa: bool = True,
    ) -> torch.Tensor:
        batch_size, seq_len, _ = x.shape

        # Linear projections & split into heads: [batch, heads, seq_len, head_dim]
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)

        # Apply RoPE
        cos, sin = self.rotary_emb(v, seq_len)
        q, k = apply_rotary_pos_emb(q, k, cos, sin)

        if use_sdpa and hasattr(F, "scaled_dot_product_attention") and attention_mask is None:
            # High-performance PyTorch causal attention
            out = F.scaled_dot_product_attention(
                q, k, v,
                attn_mask=None,
                dropout_p=self.dropout_rate if self.training else 0.0,
                is_causal=True
            )
        else:
            # Explicit causal masking computation for auditing and verification
            scale = 1.0 / math.sqrt(self.head_dim)
            scores = torch.matmul(q, k.transpose(-2, -1)) * scale  # [batch, heads, seq_len, seq_len]

            # Causal mask: upper triangle is -inf
            causal_mask = torch.triu(
                torch.full((seq_len, seq_len), float("-inf"), device=x.device, dtype=scores.dtype),
                diagonal=1
            )
            scores = scores + causal_mask.unsqueeze(0).unsqueeze(0)

            if attention_mask is not None:
                scores = scores + attention_mask

            probs = F.softmax(scores, dim=-1)
            probs = self.dropout(probs)
            out = torch.matmul(probs, v)

        # Merge heads: [batch, seq_len, hidden_dim]
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_dim)
        return self.out_proj(out)
