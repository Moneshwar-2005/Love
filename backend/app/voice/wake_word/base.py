"""
Abstract Base Interface for Wake-Word Detectors (Phase 06).
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from backend.app.voice.schemas import WakeWordStatus


class BaseWakeWordDetector(ABC):
    """
    Standard interface contract for acoustic wake-word detection engines.
    Always-listening operations are strictly opt-in and require explicit user consent.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider identifier (e.g. 'openwakeword', 'mock')."""
        pass

    @property
    @abstractmethod
    def target_phrase(self) -> str:
        """The canonical target wake phrase (e.g. 'Hey LOVE')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the engine libraries are available."""
        pass

    @abstractmethod
    def is_model_available(self) -> bool:
        """Returns True only if the acoustic model for 'Hey LOVE' exists locally."""
        pass

    @abstractmethod
    def get_status(self) -> WakeWordStatus:
        """Returns current operational status, model readiness, and mic state."""
        pass

    @abstractmethod
    def set_active(self, active: bool, mic_permission: bool = False) -> WakeWordStatus:
        """Enables or disables live acoustic monitoring."""
        pass

    @abstractmethod
    def detect_in_audio(self, audio_bytes: bytes) -> Tuple[bool, float]:
        """
        Processes normalized 16kHz audio buffer and returns: (detected: bool, confidence: float).
        """
        pass
