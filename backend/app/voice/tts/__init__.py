"""
Text-to-Speech provider registry and routing factory (Phase 06).
"""

from typing import Any, Dict, List, Optional
from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.exceptions import TTSProviderNotConfiguredError, VoicePrivacyRestrictionError
from backend.app.voice.tts.azure_speech import AzureSpeechTTSProvider
from backend.app.voice.tts.base import BaseTTSProvider
from backend.app.voice.tts.elevenlabs import ElevenLabsTTSProvider
from backend.app.voice.tts.mock_tts import MockTTSProvider
from backend.app.voice.tts.piper import PiperTTSProvider

_tts_instances: Dict[str, BaseTTSProvider] = {}


def _get_instance(provider_id: str) -> BaseTTSProvider:
    if provider_id not in _tts_instances:
        if provider_id == "azure":
            _tts_instances[provider_id] = AzureSpeechTTSProvider()
        elif provider_id == "elevenlabs":
            _tts_instances[provider_id] = ElevenLabsTTSProvider()
        elif provider_id == "piper":
            _tts_instances[provider_id] = PiperTTSProvider()
        elif provider_id == "mock":
            _tts_instances[provider_id] = MockTTSProvider()
        else:
            raise TTSProviderNotConfiguredError(provider_id, f"Unknown TTS provider '{provider_id}'.")
    return _tts_instances[provider_id]


async def get_tts_provider(provider_id: Optional[str] = None) -> BaseTTSProvider:
    """
    Resolves the appropriate TTS provider based on requested ID, configuration, and privacy policy.
    Supports auto-selection with local-fallback.
    """
    settings = get_settings()
    target_id = (provider_id or settings.VOICE_TTS_PROVIDER).lower()

    # Privacy constraint
    if settings.LOCAL_ONLY_MODE and target_id in ("azure", "elevenlabs"):
        raise VoicePrivacyRestrictionError(
            target_id, "LOCAL_ONLY_MODE prohibits routing to cloud TTS providers."
        )

    # Specific provider requested
    if target_id not in ("auto", ""):
        provider = _get_instance(target_id)
        if not provider.is_configured():
            if settings.VOICE_TTS_LOCAL_FALLBACK and target_id != "mock":
                logger.warning(
                    f"Requested TTS provider '{target_id}' is NOT CONFIGURED. Falling back to mock local provider."
                )
                return _get_instance("mock")
            raise TTSProviderNotConfiguredError(
                target_id, f"Provider '{target_id}' credentials or model weights are missing."
            )
        return provider

    # Auto-selection logic
    # 1. Under LOCAL_ONLY_MODE: Piper -> Mock
    if settings.LOCAL_ONLY_MODE:
        piper = _get_instance("piper")
        if piper.is_configured() and await piper.is_available():
            return piper
        return _get_instance("mock")

    # 2. Standard priority: Azure -> ElevenLabs -> Piper -> Mock
    azure = _get_instance("azure")
    if azure.is_configured() and await azure.is_available():
        return azure

    eleven = _get_instance("elevenlabs")
    if eleven.is_configured() and await eleven.is_available():
        return eleven

    piper = _get_instance("piper")
    if piper.is_configured() and await piper.is_available():
        return piper

    # 3. Local fallback
    if settings.VOICE_TTS_LOCAL_FALLBACK:
        return _get_instance("mock")

    raise TTSProviderNotConfiguredError(
        "auto", "No configured TTS provider is currently available and local fallback is disabled."
    )


async def list_tts_providers() -> List[Dict[str, Any]]:
    """Returns status and configuration readiness for all TTS providers."""
    providers = [
        _get_instance("azure"),
        _get_instance("elevenlabs"),
        _get_instance("piper"),
        _get_instance("mock"),
    ]
    results = []
    for p in providers:
        results.append({
            "provider_id": p.provider_id,
            "name": p.name,
            "is_local": p.is_local,
            "is_configured": p.is_configured(),
            "is_available": await p.is_available(),
        })
    return results


__all__ = [
    "BaseTTSProvider",
    "AzureSpeechTTSProvider",
    "ElevenLabsTTSProvider",
    "PiperTTSProvider",
    "MockTTSProvider",
    "get_tts_provider",
    "list_tts_providers",
]
