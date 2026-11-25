"""Sequence Packing and Causal Batch DataLoader for LOVE Native AI.

Implements Section 5 (NAI-04):
- Efficient sequence packing of variable-length documents.
- Separator token handling (<|endoftext|>, ID 2).
- Proper causal target shifting (inputs = seq[:-1], targets = seq[1:]).
- Padding and attention mask compatibility.
- Future-token leakage prevention.
- Truncation, packing, and padding accounting.
"""
from typing import Dict, Any, List, Optional, Tuple, Iterator
import numpy as np
import torch

from native_ai.data_cache.binary_cache import BinaryTokenDataset
from native_ai.data_cache.sampler import DomainWeightedSampler

EOS_TOKEN_ID = 2  # <|endoftext|> in LOVE Tokenizer v0.1
PAD_TOKEN_ID = 0  # <|pad|> in LOVE Tokenizer v0.1


class CausalDataLoader:
    """
    DataLoader generating packed or padded batches of causal language modeling pairs (inputs, targets).
    Guarantees strict next-token alignment: inputs = seq[:-1], targets = seq[1:].
    """

    def __init__(
        self,
        dataset: BinaryTokenDataset,
        batch_size: int = 1,
        sequence_length: int = 512,
        sampler: Optional[DomainWeightedSampler] = None,
        packing: bool = True,
        drop_last: bool = False,
        seed: int = 42,
    ):
        self.dataset = dataset
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.sampler = sampler
        self.packing = packing
        self.drop_last = drop_last
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Telemetry
        self.telemetry = {
            "batches_generated": 0,
            "sequences_generated": 0,
            "total_tokens_emitted": 0,
            "documents_packed": 0,
            "truncated_documents": 0,
            "padding_tokens_inserted": 0,
            "eos_separators_inserted": 0,
        }

    def _get_document(self, doc_idx: int) -> Tuple[np.ndarray, str]:
        if self.sampler is not None:
            _, tokens, cat = self.sampler.sample_document()
            return tokens, cat
        else:
            tokens, cat = self.dataset.get_document(doc_idx)
            return tokens, cat

    def __iter__(self) -> Iterator[Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]]:
        """
        Yields batches of (input_ids, targets, attention_mask):
        - input_ids: torch.LongTensor of shape [batch_size, sequence_length]
        - targets: torch.LongTensor of shape [batch_size, sequence_length]
        - attention_mask: torch.LongTensor of shape [batch_size, sequence_length] (1 for valid, 0 for pad)
        """
        required_len = self.sequence_length + 1  # 1 extra token for target shift

        buffer: List[int] = []
        doc_cursor = 0
        total_docs = self.dataset.num_documents

        while True:
            batch_inputs = []
            batch_targets = []
            batch_masks = []

            for _ in range(self.batch_size):
                if self.packing:
                    # Sequence packing mode: fill buffer up to required_len
                    while len(buffer) < required_len:
                        if self.sampler is None and doc_cursor >= total_docs:
                            # End of sequential epoch
                            break

                        tokens, _ = self._get_document(doc_cursor)
                        doc_cursor += 1
                        self.telemetry["documents_packed"] += 1

                        # Append document tokens followed by EOS separator
                        buffer.extend(tokens.tolist())
                        buffer.append(EOS_TOKEN_ID)
                        self.telemetry["eos_separators_inserted"] += 1

                    if len(buffer) < required_len:
                        # Reached end of data in sequential mode without enough tokens
                        if self.drop_last or len(buffer) <= 1:
                            break
                        # Pad the remaining buffer
                        pad_len = required_len - len(buffer)
                        seq = buffer + [PAD_TOKEN_ID] * pad_len
                        mask = [1] * len(buffer) + [0] * pad_len
                        buffer = []
                        self.telemetry["padding_tokens_inserted"] += pad_len
                    else:
                        seq = buffer[:required_len]
                        buffer = buffer[required_len:]
                        mask = [1] * required_len

                else:
                    # Non-packing mode: 1 document per sequence, truncated or padded
                    if self.sampler is None and doc_cursor >= total_docs:
                        break

                    tokens, _ = self._get_document(doc_cursor)
                    doc_cursor += 1

                    doc_tokens = tokens.tolist()
                    if len(doc_tokens) > required_len:
                        seq = doc_tokens[:required_len]
                        mask = [1] * required_len
                        self.telemetry["truncated_documents"] += 1
                    else:
                        pad_len = required_len - len(doc_tokens)
                        seq = doc_tokens + [PAD_TOKEN_ID] * pad_len
                        mask = [1] * len(doc_tokens) + [0] * pad_len
                        self.telemetry["padding_tokens_inserted"] += pad_len

                # Create shifted inputs and targets
                # input_ids: seq[0 : sequence_length]
                # targets:   seq[1 : sequence_length + 1]
                inp = seq[: self.sequence_length]
                tgt = seq[1 : self.sequence_length + 1]
                m = mask[: self.sequence_length]

                batch_inputs.append(inp)
                batch_targets.append(tgt)
                batch_masks.append(m)
                self.telemetry["sequences_generated"] += 1
                self.telemetry["total_tokens_emitted"] += self.sequence_length

            if len(batch_inputs) == 0:
                break
            if len(batch_inputs) < self.batch_size and self.drop_last:
                break

            self.telemetry["batches_generated"] += 1

            inp_tensor = torch.tensor(batch_inputs, dtype=torch.long)
            tgt_tensor = torch.tensor(batch_targets, dtype=torch.long)
            mask_tensor = torch.tensor(batch_masks, dtype=torch.long)

            yield inp_tensor, tgt_tensor, mask_tensor

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns batching telemetry and packing statistics."""
        return dict(self.telemetry)
