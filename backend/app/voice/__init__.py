"""
LOVE Voice Engine, Speech Recognition & Wake Word Subsystem (Phase 06).
"""

from backend.app.voice.audio import (
    convert_to_wav_16k_mono,
    detect_audio_format,
    generate_synthetic_wav,
    validate_audio_payload,
)
from backend.app.voice.exceptions import (
    AudioValidationError,
    STTError,
    STTProviderNotConfiguredError,
    TTSError,
    TTSProviderNotConfiguredError,
    VoiceException,
    VoicePrivacyRestrictionError,
    VoiceSessionError,
    WakeWordError,
    WakeWordModelNotFoundError,
)
from backend.app.voice.orchestrator import VoiceOrchestrationService, get_voice_service
from backend.app.voice.personality import (
    LOVE_CLASSIC_PROFILE,
    build_ssml,
    get_active_voice_profile,
    list_available_profiles,
)
from backend.app.voice.schemas import (
    AudioFormat,
    STTProviderType,
    SynthesisResult,
    TTSProviderType,
    TranscriptionResult,
    TranscriptionSegment,
    VoiceChatResponse,
    VoiceProfile,
    VoiceSessionResponse,
    VoiceSessionState,
    VoiceStatusResponse,
    WakeWordProviderType,
    WakeWordStatus,
)
from backend.app.voice.session import VoiceSession, VoiceSessionManager, get_voice_session_manager

__all__ = [
    "VoiceOrchestrationService",
    "get_voice_service",
    "VoiceSessionManager",
    "get_voice_session_manager",
    "VoiceSession",
    "VoiceSessionState",
    "VoiceSessionResponse",
    "TranscriptionResult",
    "TranscriptionSegment",
    "SynthesisResult",
    "VoiceProfile",
    "WakeWordStatus",
    "VoiceChatResponse",
    "VoiceStatusResponse",
    "LOVE_CLASSIC_PROFILE",
    "get_active_voice_profile",
    "list_available_profiles",
    "build_ssml",
    "validate_audio_payload",
    "convert_to_wav_16k_mono",
    "detect_audio_format",
    "generate_synthetic_wav",
    "VoiceException",
    "AudioValidationError",
    "STTError",
    "STTProviderNotConfiguredError",
    "TTSError",
    "TTSProviderNotConfiguredError",
    "WakeWordError",
    "WakeWordModelNotFoundError",
    "VoiceSessionError",
    "VoicePrivacyRestrictionError",
]
