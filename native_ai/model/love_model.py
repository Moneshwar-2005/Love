"""LOVE Native AI Transformer Architecture and Causal Language Model.

Provides complete decoder-only Transformer model, configuration management,
parameter counting, tied embeddings, and autoregressive generation.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
import yaml
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from native_ai.model.embeddings import TokenEmbedding
from native_ai.model.normalization import RMSNorm
from native_ai.model.transformer_block import TransformerBlock

@dataclass
class LoveModelConfig:
    model_name: str = "love-native-tiny"
    architecture: str = "decoder-only-transformer"
    vocab_size: int = 8192
    context_length: int = 512
    layers: int = 4
    heads: int = 4
    hidden_dim: int = 256
    head_dim: int = 64
    ffn_dim: int = 768
    positional_encoding: str = "rope"
    normalization: str = "rmsnorm"
    norm_eps: float = 1e-5
    attention: str = "causal_self_attention"
    ffn_activation: str = "swiglu"
    rope_base: float = 10000.0
    tie_embeddings: bool = True
    dropout: float = 0.0
    init_method: str = "normal"
    init_std: float = 0.02
    use_activation_checkpointing: bool = False

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "LoveModelConfig":
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**filtered)
        cfg.validate()
        return cfg

    def to_yaml(self, yaml_path: str) -> None:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(asdict(self), f, sort_keys=False)

    def validate(self) -> None:
        assert self.vocab_size > 0, "vocab_size must be positive"
        assert self.context_length > 0, "context_length must be positive"
        assert self.layers > 0, "layers must be positive"
        assert self.heads > 0, "heads must be positive"
        assert self.hidden_dim > 0, "hidden_dim must be positive"
        assert self.hidden_dim == self.heads * self.head_dim, (
            f"hidden_dim ({self.hidden_dim}) must equal heads ({self.heads}) * head_dim ({self.head_dim})"
        )
        assert self.ffn_dim > 0, "ffn_dim must be positive"
        assert self.positional_encoding in ["rope"], f"Unsupported positional_encoding: {self.positional_encoding}"
        assert self.normalization in ["rmsnorm"], f"Unsupported normalization: {self.normalization}"
        assert self.ffn_activation in ["swiglu"], f"Unsupported ffn_activation: {self.ffn_activation}"


class LoveForCausalLM(nn.Module):
    """Full Decoder-Only Language Model for LOVE Native AI."""
    def __init__(self, config: LoveModelConfig):
        super().__init__()
        config.validate()
        self.config = config

        self.token_embeddings = TokenEmbedding(config.vocab_size, config.hidden_dim)
        self.layers = nn.ModuleList([
            TransformerBlock(
                hidden_dim=config.hidden_dim,
                n_heads=config.heads,
                head_dim=config.head_dim,
                ffn_dim=config.ffn_dim,
                max_seq_len=config.context_length,
                norm_eps=config.norm_eps,
                rope_base=config.rope_base,
                dropout=config.dropout,
            )
            for _ in range(config.layers)
        ])
        self.final_norm = RMSNorm(config.hidden_dim, eps=config.norm_eps)
        self.lm_head = nn.Linear(config.hidden_dim, config.vocab_size, bias=False)

        # Weight tying: tie output projection weights to token embeddings
        if config.tie_embeddings:
            self.lm_head.weight = self.token_embeddings.embedding.weight

        # Weight initialization
        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=self.config.init_std)
        elif isinstance(module, RMSNorm):
            nn.init.ones_(module.weight)

    def forward(
        self,
        input_ids: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        use_sdpa: bool = True,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Args:
            input_ids: [batch_size, seq_len] tensor of integer token IDs
            targets: Optional [batch_size, seq_len] tensor of target token IDs
            use_sdpa: Whether to use scaled dot-product attention
        Returns:
            logits: [batch_size, seq_len, vocab_size]
            loss: scalar CrossEntropyLoss if targets is provided, else None
        """
        batch_size, seq_len = input_ids.shape
        if seq_len > self.config.context_length:
            raise ValueError(
                f"Sequence length {seq_len} exceeds context length {self.config.context_length}"
            )

        x = self.token_embeddings(input_ids)

        for layer in self.layers:
            if self.config.use_activation_checkpointing and self.training:
                x = checkpoint(layer, x, None, use_sdpa, use_reentrant=False)
            else:
                x = layer(x, attention_mask=None, use_sdpa=use_sdpa)

        x = self.final_norm(x)
        logits = self.lm_head(x)

        loss = None
        if targets is not None:
            # Flatten tokens for cross entropy loss
            loss = F.cross_entropy(logits.view(-1, self.config.vocab_size), targets.view(-1))

        return logits, loss

    def count_parameters(self) -> Dict[str, Any]:
        """Calculates total and unique trainable parameters."""
        unique_params = sum(
            p.numel() for p in {p.data_ptr(): p for p in self.parameters() if p.requires_grad}.values()
        )
        embedding_params = self.token_embeddings.embedding.weight.numel()
        non_embedding_params = sum(
            p.numel()
            for name, p in self.named_parameters()
            if "token_embeddings" not in name and "lm_head" not in name
        )
        untied_total = (
            unique_params + embedding_params if self.config.tie_embeddings else unique_params
        )
        return {
            "total_parameters": unique_params,
            "unique_trainable_parameters": unique_params,
            "untied_total_parameters": untied_total,
            "non_embedding_parameters": non_embedding_params,
            "embedding_parameters": embedding_params,
            "tied_embeddings": self.config.tie_embeddings,
        }

    @torch.no_grad()
    def generate(
        self,
        prompt_ids: torch.Tensor,
        max_new_tokens: int = 32,
        temperature: float = 1.0,
        top_k: Optional[int] = 50,
    ) -> torch.Tensor:
        """Autoregressive text generation with temperature and top-k filtering."""
        self.eval()
        generated = prompt_ids.clone()

        for _ in range(max_new_tokens):
            idx_cond = (
                generated
                if generated.size(1) <= self.config.context_length
                else generated[:, -self.config.context_length:]
            )
            logits, _ = self(idx_cond)
            next_logits = logits[:, -1, :]  # [batch_size, vocab_size]

            if temperature <= 0.0:
                next_token = torch.argmax(next_logits, dim=-1, keepdim=True)
            else:
                next_logits = next_logits / temperature
                if top_k is not None and top_k > 0:
                    v, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
                    next_logits[next_logits < v[:, [-1]]] = float("-inf")
                probs = F.softmax(next_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

            generated = torch.cat((generated, next_token), dim=1)

        return generated
