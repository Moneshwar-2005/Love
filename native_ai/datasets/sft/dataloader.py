"""SFT Dataset, Collator, and DataLoader Infrastructure for LOVE Native AI (NAI-07A).

Provides:
- SFTDataset: Dataset for loading and tokenizing ConversationExamples.
- SFTCollator: Dynamic batch padding with -100 target masking for padding positions.
- SFTDataLoader: Deterministic batched loader for SFT training and evaluation.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import torch
from torch.utils.data import Dataset, DataLoader

from native_ai.datasets.sft.format import (
    ConversationExample,
    LOVEInstructionFormatter,
    PAD_TOKEN_ID,
    IGNORE_INDEX,
    TruncationSafetyError,
)


class SFTDataset(Dataset):
    """
    Dataset of Supervised Fine-Tuning examples encoded for causal language modeling.
    Pre-encodes examples into (input_ids, target_ids) pairs with assistant-only loss masking.
    """

    def __init__(
        self,
        jsonl_path: Union[str, Path],
        tokenizer: Any,
        max_seq_len: int = 512,
        allow_turn_truncation: bool = True,
    ):
        self.jsonl_path = Path(jsonl_path)
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.allow_turn_truncation = allow_turn_truncation

        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"SFT split file not found: {self.jsonl_path}")

        self.examples: List[ConversationExample] = []
        self.encoded_pairs: List[Tuple[List[int], List[int]]] = []
        self.skipped_count = 0

        self._load_and_encode()

    def _load_and_encode(self) -> None:
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    example = ConversationExample.from_dict(data)
                    inp, tgt = LOVEInstructionFormatter.encode_conversation(
                        example=example,
                        tokenizer=self.tokenizer,
                        max_seq_len=self.max_seq_len,
                        allow_turn_truncation=self.allow_turn_truncation,
                    )
                    self.examples.append(example)
                    self.encoded_pairs.append((inp, tgt))
                except (ValueError, TruncationSafetyError, json.JSONDecodeError):
                    self.skipped_count += 1
                    continue

    def __len__(self) -> int:
        return len(self.encoded_pairs)

    def __getitem__(self, idx: int) -> Tuple[List[int], List[int]]:
        return self.encoded_pairs[idx]

    def get_example(self, idx: int) -> ConversationExample:
        return self.examples[idx]


class SFTCollator:
    """
    Collator for batching variable-length SFT examples.
    Pads input_ids with PAD_TOKEN_ID (0).
    Pads targets with IGNORE_INDEX (-100).
    Builds attention_mask (1 for valid tokens, 0 for padding).
    """

    def __init__(
        self,
        pad_token_id: int = PAD_TOKEN_ID,
        ignore_index: int = IGNORE_INDEX,
        max_seq_len: Optional[int] = 512,
    ):
        self.pad_token_id = pad_token_id
        self.ignore_index = ignore_index
        self.max_seq_len = max_seq_len

    def __call__(
        self,
        batch: List[Tuple[List[int], List[int]]],
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if not batch:
            raise ValueError("Cannot collate an empty batch.")

        batch_max_len = max(len(inp) for inp, _ in batch)
        if self.max_seq_len is not None:
            batch_max_len = min(batch_max_len, self.max_seq_len)

        batch_inputs = []
        batch_targets = []
        batch_masks = []

        for inp, tgt in batch:
            # Bound to batch_max_len
            cur_inp = inp[:batch_max_len]
            cur_tgt = tgt[:batch_max_len]
            pad_len = batch_max_len - len(cur_inp)

            padded_inp = cur_inp + [self.pad_token_id] * pad_len
            padded_tgt = cur_tgt + [self.ignore_index] * pad_len
            mask = [1] * len(cur_inp) + [0] * pad_len

            batch_inputs.append(padded_inp)
            batch_targets.append(padded_tgt)
            batch_masks.append(mask)

        input_ids = torch.tensor(batch_inputs, dtype=torch.long)
        targets = torch.tensor(batch_targets, dtype=torch.long)
        attention_mask = torch.tensor(batch_masks, dtype=torch.long)

        return input_ids, targets, attention_mask


class SFTDataLoader(DataLoader):
    """Deterministic DataLoader for SFT."""

    def __init__(
        self,
        dataset: SFTDataset,
        batch_size: int = 1,
        shuffle: bool = False,
        seed: int = 42,
        drop_last: bool = False,
        **kwargs,
    ):
        collator = SFTCollator(
            pad_token_id=PAD_TOKEN_ID,
            ignore_index=IGNORE_INDEX,
            max_seq_len=dataset.max_seq_len,
        )
        generator = torch.Generator()
        generator.manual_seed(seed)
        super().__init__(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            collate_fn=collator,
            drop_last=drop_last,
            generator=generator if shuffle else None,
            **kwargs,
        )


def create_sft_dataloader(
    dataset: SFTDataset,
    batch_size: int = 1,
    shuffle: bool = False,
    seed: int = 42,
    drop_last: bool = False,
) -> SFTDataLoader:
    """Creates a deterministic SFTDataLoader instance."""
    return SFTDataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        seed=seed,
        drop_last=drop_last,
    )
