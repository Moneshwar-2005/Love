"""Token Embedding Layer for LOVE Native AI.

Converts token IDs into dense hidden vectors and enforces strict
vocabulary boundary checks.
"""
import torch
import torch.nn as nn

class TokenEmbedding(nn.Module):
    def __init__(self, vocab_size: int, hidden_dim: int):
        super().__init__()
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.embedding = nn.Embedding(vocab_size, hidden_dim)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        # Strict boundary validation
        if (input_ids < 0).any() or (input_ids >= self.vocab_size).any():
            min_val = input_ids.min().item()
            max_val = input_ids.max().item()
            raise ValueError(
                f"Token ID out of bounds. Valid range [0, {self.vocab_size - 1}], "
                f"found min {min_val}, max {max_val}"
            )
        return self.embedding(input_ids)
