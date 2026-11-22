"""
Abstract Base Provider Interface for Text-To-Speech (TTS) runtimes (Phase 06).
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from backend.app.voice.schemas import SynthesisResult, VoiceProfile


class BaseTTSProvider(ABC):
    """
    Standard interface contract for Text-To-Speech synthesizers.
    Decouples voice generation from vendor-specific runtimes (Azure, ElevenLabs, Piper, Mock).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'azure', 'elevenlabs', 'piper', 'mock')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider label."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider executes strictly on the host without cloud network calls."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has all required credentials or models configured."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Performs a live connectivity or binary check to verify synthesis capability."""
        pass

    @abstractmethod
    async def list_voices(self) -> List[Dict[str, Any]]:
        """Enumerates available voices for this provider."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> SynthesisResult:
        """
        Synthesizes text into complete audio bytes and structured metadata.
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Streams audio chunk bytes as they are synthesized.
        """
        pass
