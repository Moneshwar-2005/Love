"""
Deterministic Offline Feature-Hashing Embedding Provider (Phase 04).
Guarantees resilient on-device semantic similarity when neural embedding servers are offline.
"""

import hashlib
import re
from typing import List
import numpy as np

from backend.app.memory.embeddings.base import BaseEmbeddingProvider


class DeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """
    100% local, zero-network, deterministic dense feature-hashing embedding provider.
    Computes normalized 128-dimensional vectors based on word tokens, character trigrams,
    and semantic feature hashing.
    """

    def __init__(self, dimension: int = 128):
        self._dimension = dimension

    @property
    def provider_id(self) -> str:
        return "deterministic"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_local(self) -> bool:
        return True

    async def is_available(self) -> bool:
        """Always available immediately without network or external dependencies."""
        return True

    async def embed_text(self, text: str) -> List[float]:
        """
        Maps text to a normalized dense vector via token and n-gram feature hashing.
        """
        vector = np.zeros(self._dimension, dtype=np.float32)
        clean_text = text.lower().strip()
        tokens = re.findall(r"\w+", clean_text)

        if not tokens:
            return vector.tolist()

        # 1. Word token hashing
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vector[idx] += sign * 1.5

        # 2. Character trigram hashing for typo-tolerance and subword semantics
        padded = f"_{clean_text}_"
        for i in range(len(padded) - 2):
            trigram = padded[i:i+3]
            h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if ((h >> 4) & 1) else -1.0
            vector[idx] += sign * 0.5

        # Normalize vector to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()
