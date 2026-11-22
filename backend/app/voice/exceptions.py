"""
Domain-specific exceptions for the Voice Engine, Speech Recognition & Wake Word (Phase 06).
"""

from typing import Optional
from backend.app.core.exceptions import AppException


class VoiceException(AppException):
    """Base exception for all voice engine, speech processing, and audio errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class AudioValidationError(VoiceException):
    """Raised when uploaded audio fails format, sample rate, duration, or size validation."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message=message, status_code=400, details=details)


class STTError(VoiceException):
    """Raised when speech-to-text transcription fails."""
    def __init__(self, provider: str, message: str, details: Optional[dict] = None):
        merged = {"provider": provider}
        if details:
            merged.update(details)
        super().__init__(
            message=f"Speech-to-text error ({provider}): {message}",
            status_code=500,
            details=merged
        )


class STTProviderNotConfiguredError(VoiceException):
    """Raised when the requested STT provider is not configured or model is missing."""
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"STT provider '{provider}' is NOT CONFIGURED: {reason}",
            status_code=503,
            details={"provider": provider, "reason": reason}
        )


class TTSError(VoiceException):
    """Raised when text-to-speech synthesis fails."""
    def __init__(self, provider: str, message: str, details: Optional[dict] = None):
        merged = {"provider": provider}
        if details:
            merged.update(details)
        super().__init__(
            message=f"Text-to-speech error ({provider}): {message}",
            status_code=500,
            details=merged
        )


class TTSProviderNotConfiguredError(VoiceException):
    """Raised when the requested TTS provider has missing credentials or models."""
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"TTS provider '{provider}' is NOT CONFIGURED: {reason}",
            status_code=503,
            details={"provider": provider, "reason": reason}
        )


class WakeWordError(VoiceException):
    """Raised when wake-word detection encounters an operational failure."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message=f"Wake-word error: {message}", status_code=500, details=details)


class WakeWordModelNotFoundError(VoiceException):
    """Raised when the custom wake-word model for 'Hey LOVE' is not found."""
    def __init__(self, phrase: str, path: str):
        super().__init__(
            message=f"Custom wake-word model for phrase '{phrase}' not found at '{path}'. See documentation for training requirements.",
            status_code=404,
            details={"phrase": phrase, "expected_path": path}
        )


class VoiceSessionError(VoiceException):
    """Raised when voice session management encounters an illegal transition or concurrency conflict."""
    def __init__(self, message: str, status_code: int = 409, details: Optional[dict] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class VoicePrivacyRestrictionError(VoiceException):
    """Raised when audio operations violate LOCAL_ONLY_MODE or cloud privacy constraints."""
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"Voice privacy restriction: Cannot use cloud provider '{provider}' under current privacy policy ({reason}).",
            status_code=403,
            details={"provider": provider, "reason": reason}
        )
