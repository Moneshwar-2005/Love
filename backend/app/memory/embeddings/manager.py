"""
Embedding Manager for Persistent Personal Memory (Phase 04).
"""

from typing import Dict, List, Optional
from backend.app.config.settings import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.memory.embeddings.base import BaseEmbeddingProvider
from backend.app.memory.embeddings.deterministic import DeterministicEmbeddingProvider
from backend.app.memory.embeddings.gemini import GeminiEmbeddingProvider
from backend.app.memory.embeddings.ollama import OllamaEmbeddingProvider
from backend.app.memory.exceptions import EmbeddingUnavailableError

logger = get_logger("memory.embeddings.manager")


class EmbeddingManager:
    """
    Manages embedding provider resolution, dimension checks, and privacy enforcement.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        primary_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.settings = settings or get_settings()
        self._primary_provider = primary_provider
        self._providers: Dict[str, BaseEmbeddingProvider] = {}
        self._initialize_providers()
        if primary_provider:
            self._providers[primary_provider.provider_id] = primary_provider

    def _initialize_providers(self) -> None:
        """Instantiates all registered embedding adapters."""
        # 1. Deterministic local fallback
        self._providers["deterministic"] = DeterministicEmbeddingProvider(dimension=128)

        # 2. Ollama local
        self._providers["ollama"] = OllamaEmbeddingProvider(
            base_url=self.settings.OLLAMA_BASE_URL,
            model=self.settings.MEMORY_OLLAMA_EMBEDDING_MODEL,
        )

        # 3. Google Gemini (Cloud)
        self._providers["gemini"] = GeminiEmbeddingProvider(
            api_key=self.settings.GEMINI_API_KEY,
            base_url=self.settings.GEMINI_BASE_URL,
            allow_cloud=self.settings.MEMORY_ALLOW_CLOUD_EMBEDDINGS,
            local_only_mode=self.settings.LOCAL_ONLY_MODE,
        )

    async def get_active_provider(self) -> BaseEmbeddingProvider:
        """
        Dynamically selects the best available embedding provider respecting configured policies.
        Priority:
        1. Explicit configuration preference if available.
        2. Local Ollama if running.
        3. Cloud Gemini (if permitted and local_only is False).
        4. Deterministic local feature hashing (guaranteed fallback).
        """
        if self._primary_provider and await self._primary_provider.is_available():
            return self._primary_provider

        pref = self.settings.MEMORY_EMBEDDING_PROVIDER.lower()

        # Handle explicit preference
        if pref in self._providers:
            provider = self._providers[pref]
            if await provider.is_available():
                return provider

        # If preference is "auto" or requested was unavailable:
        # Check Ollama first if local-only or auto
        ollama = self._providers["ollama"]
        if await ollama.is_available():
            return ollama

        # Check cloud Gemini only if explicitly permitted
        if self.settings.MEMORY_ALLOW_CLOUD_EMBEDDINGS and not self.settings.LOCAL_ONLY_MODE:
            gemini = self._providers["gemini"]
            if await gemini.is_available():
                return gemini

        # Default resilient fallback: Deterministic local
        return self._providers["deterministic"]

    async def embed_text(self, text: str) -> List[float]:
        """Generates embedding using the resolved active provider."""
        provider = await self.get_active_provider()
        return await provider.embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation using active provider."""
        provider = await self.get_active_provider()
        return await provider.embed_batch(texts)
