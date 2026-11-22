"""
Abstract Base Provider Interface for Speech-To-Text (STT) runtimes (Phase 06).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from backend.app.voice.schemas import TranscriptionResult


class BaseSTTProvider(ABC):
    """
    Standard interface contract for all Speech-to-Text providers.
    Ensures interchangeable STT runtimes (faster-whisper, mock, future providers).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine-readable provider identifier (e.g. 'faster_whisper', 'mock')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider label."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider runs completely locally on the host machine."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has necessary configuration / models specified."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Performs a live readiness check to verify model presence or service connectivity."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> TranscriptionResult:
        """
        Transcribes normalized audio bytes into structured text, segments, and metadata.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Returns metadata about the active model, compute device, and quantization."""
        pass
