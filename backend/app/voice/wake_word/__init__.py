"""
Wake-word detector factory and registry (Phase 06).
"""

from typing import Dict, Optional
from backend.app.config.settings import get_settings
from backend.app.voice.wake_word.base import BaseWakeWordDetector
from backend.app.voice.wake_word.mock_wake_word import MockWakeWordDetector
from backend.app.voice.wake_word.openwakeword import OpenWakeWordDetector

_wake_word_detectors: Dict[str, BaseWakeWordDetector] = {}


def get_wake_word_detector(provider_id: Optional[str] = None) -> BaseWakeWordDetector:
    """Returns active wake-word detector instance."""
    settings = get_settings()
    target_id = (provider_id or settings.VOICE_WAKE_WORD_PROVIDER).lower()

    if target_id not in _wake_word_detectors:
        if target_id == "openwakeword":
            _wake_word_detectors[target_id] = OpenWakeWordDetector()
        elif target_id == "mock":
            _wake_word_detectors[target_id] = MockWakeWordDetector()
        else:
            _wake_word_detectors[target_id] = OpenWakeWordDetector()

    return _wake_word_detectors[target_id]


__all__ = [
    "BaseWakeWordDetector",
    "OpenWakeWordDetector",
    "MockWakeWordDetector",
    "get_wake_word_detector",
]
