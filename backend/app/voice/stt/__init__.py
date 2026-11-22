"""
Speech-to-Text provider registry and factory (Phase 06).
"""

from typing import Dict, List, Optional
from backend.app.config.settings import get_settings
from backend.app.voice.stt.base import BaseSTTProvider
from backend.app.voice.stt.faster_whisper import FasterWhisperSTTProvider
from backend.app.voice.stt.mock_stt import MockSTTProvider


_stt_providers: Dict[str, BaseSTTProvider] = {}


def get_stt_provider(provider_id: Optional[str] = None) -> BaseSTTProvider:
    """
    Returns the requested STT provider instance or active default from settings.
    """
    settings = get_settings()
    target_id = (provider_id or settings.VOICE_STT_PROVIDER).lower()

    if target_id not in _stt_providers:
        if target_id == "faster_whisper":
            _stt_providers[target_id] = FasterWhisperSTTProvider()
        elif target_id == "mock":
            _stt_providers[target_id] = MockSTTProvider()
        else:
            # Fallback to faster_whisper
            _stt_providers[target_id] = FasterWhisperSTTProvider()

    return _stt_providers[target_id]


def list_stt_providers() -> List[Dict[str, any]]:
    """Returns metadata for all supported STT providers."""
    providers = [
        FasterWhisperSTTProvider(),
        MockSTTProvider(),
    ]
    return [
        {
            "provider_id": p.provider_id,
            "name": p.name,
            "is_local": p.is_local,
            "is_configured": p.is_configured(),
            "model_info": p.get_model_info(),
        }
        for p in providers
    ]


__all__ = [
    "BaseSTTProvider",
    "FasterWhisperSTTProvider",
    "MockSTTProvider",
    "get_stt_provider",
    "list_stt_providers",
]
