"""
Abstract Base Provider Interface for LLM runtimes (Phase 03).
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional
from backend.app.intelligence.schemas import (
    AssistantResponse,
    ChatMessage,
    ModelCapabilities,
    StreamChunk,
)


class BaseModelProvider(ABC):
    """
    Standard contract for all AI model providers (Local Ollama, OpenAI, Anthropic, Gemini, OpenAI-compatible).
    Ensures complete decoupling between the intelligence orchestration core and vendor-specific APIs.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine-readable provider identifier (e.g. 'ollama', 'openai')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider label (e.g. 'Ollama Local Runtime', 'OpenAI')."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider runs strictly locally on the host machine."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has necessary configuration/credentials supplied."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Performs a live health check to verify endpoint connectivity and authentication."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Lists active model identifiers available on this provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AssistantResponse:
        """Generates a complete non-streaming assistant response."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Streams an assistant response chunk-by-chunk."""
        pass

    @abstractmethod
    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """Returns capability profile for a model on this provider."""
        pass
