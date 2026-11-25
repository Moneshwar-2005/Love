"""LOVE Native AI — SFT Dataset and Pipeline Package (NAI-07A).

Provides:
- LOVE Instruction Format specification and message serialization.
- Conversation tree extraction and reconstruction.
- Text cleaning, PII redaction, and deduplication.
- Group-aware deterministic split generation (tree isolation).
- Assistant-only loss masking and causal alignment.
- SFT Dataset and DataLoader infrastructure.
"""

from native_ai.datasets.sft.format import (
    Message,
    ConversationExample,
    LOVEInstructionFormatter,
    SYSTEM_TOKEN_ID,
    USER_TOKEN_ID,
    ASSISTANT_TOKEN_ID,
    EOS_TOKEN_ID,
    PAD_TOKEN_ID,
    IGNORE_INDEX,
)
from native_ai.datasets.sft.extractor import SFTDataExtractor
from native_ai.datasets.sft.pipeline import SFTPipeline
from native_ai.datasets.sft.dataloader import SFTDataset, SFTDataLoader

__all__ = [
    "Message",
    "ConversationExample",
    "LOVEInstructionFormatter",
    "SYSTEM_TOKEN_ID",
    "USER_TOKEN_ID",
    "ASSISTANT_TOKEN_ID",
    "EOS_TOKEN_ID",
    "PAD_TOKEN_ID",
    "IGNORE_INDEX",
    "SFTDataExtractor",
    "SFTPipeline",
    "SFTDataset",
    "SFTDataLoader",
]
