"""
Abstract Base Embedding Provider Interface (Phase 04).
"""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """
    Standard interface for all vector embedding providers.
    Decouples memory retrieval from specific embedding architectures.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine-readable embedding provider identifier."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Fixed dimensionality of generated vector embeddings."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this embedding provider operates 100% on-device."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Verifies whether the embedding endpoint and model are reachable."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generates a normalized float vector for a single text string."""
        pass

    async def embed(self, text: str) -> List[float]:
        """Convenience alias for embed_text."""
        return await self.embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation with default sequential fallback."""
        return [await self.embed_text(t) for t in texts]
