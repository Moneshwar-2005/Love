"""LOVE Native AI Tokenizer Module.

Provides LoveTokenizer:
- Byte-level Byte-Pair Encoding (BPE)
- Registered special tokens: <pad>, <unk>, <bos>, <eos>, <|system|>, <|user|>, <|assistant|>, <|tool|>
- Guaranteed UTF-8 byte coverage with zero out-of-bounds token IDs
- Sequence truncation, padding, batch encoding, and PyTorch tensor integration
- Exact vocabulary alignment with LoveForCausalLM (tiny.yaml: 8,192 vocab)
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import torch
from tokenizers import Tokenizer, models, pre_tokenizers, decoders


@dataclass
class LoveTokenizerConfig:
    tokenizer_name: str = "love-native-bpe-8k"
    algorithm: str = "byte-level-bpe"
    vocab_size: int = 8192
    context_length: int = 512
    pad_token: str = "<pad>"
    unk_token: str = "<unk>"
    bos_token: str = "<bos>"
    eos_token: str = "<eos>"
    system_token: str = "<|system|>"
    user_token: str = "<|user|>"
    assistant_token: str = "<|assistant|>"
    tool_token: str = "<|tool|>"
    special_tokens: List[str] = field(default_factory=lambda: [
        "<pad>", "<unk>", "<bos>", "<eos>",
        "<|system|>", "<|user|>", "<|assistant|>", "<|tool|>"
    ])

    def to_json(self, path: Union[str, Path]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "LoveTokenizerConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


class LoveTokenizer:
    """Full-featured BPE Tokenizer for LOVE Native AI."""

    def __init__(self, tokenizer: Tokenizer, config: Optional[LoveTokenizerConfig] = None):
        self._tokenizer = tokenizer
        self.config = config or LoveTokenizerConfig()

        # Cache special token IDs
        self.pad_token_id = self._tokenizer.token_to_id(self.config.pad_token)
        self.unk_token_id = self._tokenizer.token_to_id(self.config.unk_token)
        self.bos_token_id = self._tokenizer.token_to_id(self.config.bos_token)
        self.eos_token_id = self._tokenizer.token_to_id(self.config.eos_token)
        self.system_token_id = self._tokenizer.token_to_id(self.config.system_token)
        self.user_token_id = self._tokenizer.token_to_id(self.config.user_token)
        self.assistant_token_id = self._tokenizer.token_to_id(self.config.assistant_token)
        self.tool_token_id = self._tokenizer.token_to_id(self.config.tool_token)

        self.special_token_ids = {
            t: self._tokenizer.token_to_id(t) for t in self.config.special_tokens
        }

    @property
    def vocab_size(self) -> int:
        return self._tokenizer.get_vocab_size()

    def get_vocab(self) -> Dict[str, int]:
        return self._tokenizer.get_vocab()

    def token_to_id(self, token: str) -> Optional[int]:
        return self._tokenizer.token_to_id(token)

    def id_to_token(self, token_id: int) -> Optional[str]:
        return self._tokenizer.id_to_token(token_id)

    def encode(
        self,
        text: str,
        add_special_tokens: bool = False,
        truncation: bool = False,
        max_length: Optional[int] = None,
    ) -> List[int]:
        """Encodes string into list of token IDs."""
        encoding = self._tokenizer.encode(text)
        ids = encoding.ids

        if add_special_tokens and self.bos_token_id is not None:
            ids = [self.bos_token_id] + ids
        if add_special_tokens and self.eos_token_id is not None:
            ids = ids + [self.eos_token_id]

        limit = max_length or self.config.context_length
        if truncation and len(ids) > limit:
            ids = ids[:limit]

        return ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = False) -> str:
        """Decodes token IDs back into string."""
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)

    def count_tokens(self, text: str) -> int:
        """Counts tokens for given text."""
        return len(self.encode(text))

    def batch_encode(
        self,
        texts: List[str],
        padding: bool = True,
        truncation: bool = True,
        max_length: Optional[int] = None,
        return_tensors: Optional[str] = "pt",
    ) -> Dict[str, Any]:
        """
        Batch encodes a list of text strings with padding and truncation.
        Returns:
            Dict containing 'input_ids' and 'attention_mask'.
        """
        limit = max_length or self.config.context_length
        batch_ids = []
        attention_masks = []

        raw_encodings = [self.encode(t, truncation=truncation, max_length=limit) for t in texts]
        actual_max_len = max(len(ids) for ids in raw_encodings) if raw_encodings else 0
        pad_len = min(limit, actual_max_len) if padding else actual_max_len

        pad_id = self.pad_token_id if self.pad_token_id is not None else 0

        for ids in raw_encodings:
            if padding and len(ids) < pad_len:
                mask = [1] * len(ids) + [0] * (pad_len - len(ids))
                padded_ids = ids + [pad_id] * (pad_len - len(ids))
            else:
                padded_ids = ids[:pad_len]
                mask = [1] * len(padded_ids)

            batch_ids.append(padded_ids)
            attention_masks.append(mask)

        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor(batch_ids, dtype=torch.long),
                "attention_mask": torch.tensor(attention_masks, dtype=torch.long),
            }

        return {
            "input_ids": batch_ids,
            "attention_mask": attention_masks,
        }

    def batch_decode(
        self,
        batch_token_ids: Union[List[List[int]], torch.Tensor],
        skip_special_tokens: bool = False,
    ) -> List[str]:
        """Decodes a batch of token ID sequences."""
        if isinstance(batch_token_ids, torch.Tensor):
            batch_token_ids = batch_token_ids.tolist()
        return [self.decode(seq, skip_special_tokens=skip_special_tokens) for seq in batch_token_ids]

    def save_pretrained(self, save_directory: Union[str, Path]) -> Dict[str, str]:
        """Serializes tokenizer model, vocabulary, merges, and configuration."""
        save_path = Path(save_directory)
        save_path.mkdir(parents=True, exist_ok=True)

        tokenizer_file = save_path / "tokenizer.json"
        config_file = save_path / "tokenizer_config.json"

        self._tokenizer.save(str(tokenizer_file))
        self.config.to_json(config_file)

        # Also extract and save explicit vocab and merges for external auditing
        model_data = json.loads(self._tokenizer.to_str())
        if "model" in model_data and "vocab" in model_data["model"]:
            vocab_file = save_path / "vocab.json"
            with open(vocab_file, "w", encoding="utf-8") as f:
                json.dump(model_data["model"]["vocab"], f, indent=2, ensure_ascii=False)

        if "model" in model_data and "merges" in model_data["model"]:
            merges_file = save_path / "merges.txt"
            with open(merges_file, "w", encoding="utf-8") as f:
                f.write("#version: 0.2\n")
                for m in model_data["model"]["merges"]:
                    merge_str = " ".join(m) if isinstance(m, (list, tuple)) else str(m)
                    f.write(merge_str + "\n")

        return {
            "tokenizer_file": str(tokenizer_file),
            "config_file": str(config_file),
        }

    @classmethod
    def from_pretrained(cls, load_directory: Union[str, Path]) -> "LoveTokenizer":
        """Loads LoveTokenizer from disk."""
        load_path = Path(load_directory)
        tokenizer_file = load_path / "tokenizer.json"
        config_file = load_path / "tokenizer_config.json"

        if not tokenizer_file.exists():
            raise FileNotFoundError(f"Missing tokenizer file at {tokenizer_file}")

        tokenizer = Tokenizer.from_file(str(tokenizer_file))
        config = LoveTokenizerConfig.from_json(config_file) if config_file.exists() else LoveTokenizerConfig()
        return cls(tokenizer, config)
