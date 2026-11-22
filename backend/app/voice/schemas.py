"""
Pydantic schemas and data contracts for the Voice Engine, Speech Recognition & Wake Word (Phase 06).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VoiceSessionState(str, Enum):
    """Lifecycle states for a voice interaction session."""
    IDLE = "idle"
    LISTENING = "listening"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ERROR = "error"


class STTProviderType(str, Enum):
    """Supported Speech-To-Text provider runtimes."""
    FASTER_WHISPER = "faster_whisper"
    MOCK = "mock"


class TTSProviderType(str, Enum):
    """Supported Text-To-Speech provider runtimes."""
    AZURE = "azure"
    ELEVENLABS = "elevenlabs"
    PIPER = "piper"
    MOCK = "mock"
    AUTO = "auto"


class WakeWordProviderType(str, Enum):
    """Supported Wake-Word detection engines."""
    OPENWAKEWORD = "openwakeword"
    MOCK = "mock"


class AudioFormat(str, Enum):
    """Supported audio container formats."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    M4A = "m4a"
    WEBM = "webm"
    FLAC = "flac"


class TranscriptionSegment(BaseModel):
    """Segment-level transcription timing and confidence."""
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    confidence: Optional[float] = Field(None, description="Average log-probability or confidence score")


class TranscriptionResult(BaseModel):
    """Structured outcome from a speech-to-text operation."""
    text: str = Field(..., description="Complete aggregated transcribed text")
    language: str = Field(default="en", description="Detected or configured language code")
    language_probability: float = Field(default=1.0, description="Confidence in detected language")
    duration_seconds: float = Field(..., description="Input audio duration in seconds")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="Timestamped segments")
    provider: str = Field(..., description="STT provider used (e.g. faster_whisper, mock)")
    model: str = Field(..., description="Model identifier used (e.g. base, small)")


class SynthesisResult(BaseModel):
    """Structured outcome from a text-to-speech synthesis operation."""
    audio_bytes: Optional[bytes] = Field(None, exclude=True, description="Raw binary audio bytes")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio for API transmission")
    format: str = Field(default="audio/wav", description="MIME type of output audio")
    duration_seconds: float = Field(default=0.0, description="Estimated or measured duration in seconds")
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz")
    provider: str = Field(..., description="TTS provider used (e.g. azure, elevenlabs, piper, mock)")
    voice_id: str = Field(..., description="Voice name or identifier used")
    character_count: int = Field(..., description="Length of synthesized text")


class VoiceProfile(BaseModel):
    """
    Configurable Voice Personality profile for LOVE.
    Default: Elegant, calm, confident, warm, intelligent Indian English female voice with subtle futuristic nuance.
    """
    id: str = Field(default="love_classic", description="Profile identifier")
    name: str = Field(default="LOVE Classic", description="Display label")
    gender: str = Field(default="female", description="Voice gender")
    accent: str = Field(default="Indian English", description="Accent classification")
    language_code: str = Field(default="en-IN", description="BCP-47 language tag")
    description: str = Field(
        default="Intelligent, elegant, calm, confident, warm and natural female voice with Indian English pronunciation.",
        description="Personality description"
    )
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech rate multiplier (1.0 = normal)")
    pitch: float = Field(default=0.0, ge=-50.0, le=50.0, description="Pitch adjustment in percentage")
    style: str = Field(default="calm, elegant, confident, warm", description="Emotional/tonal style")
    provider_voice_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "azure": "en-IN-NeerjaNeural",
            "elevenlabs": "custom_love_voice_id",
            "piper": "en_IN-cmu_indic-medium",
            "mock": "mock_love_female_in"
        },
        description="Mapping of provider to specific voice model/name"
    )


class WakeWordStatus(BaseModel):
    """Current state and capabilities of the wake-word detection system."""
    is_enabled: bool = Field(..., description="Whether wake-word detection is globally enabled in config")
    is_active: bool = Field(..., description="Whether microphone listening is actively running")
    provider: str = Field(..., description="Wake-word engine provider")
    target_phrase: str = Field(default="Hey LOVE", description="Target wake phrase")
    threshold: float = Field(default=0.5, description="Confidence detection threshold")
    model_available: bool = Field(..., description="Whether the acoustic model for 'Hey LOVE' is present locally")
    model_path: Optional[str] = Field(None, description="Local path to custom model if available")
    mic_permission_granted: bool = Field(default=False, description="Whether user explicitly granted mic permission")
    message: str = Field(..., description="Human-readable status and training requirement notice")


class VoiceSessionCreateRequest(BaseModel):
    """Payload to initiate a new voice session."""
    conversation_id: Optional[str] = Field(None, description="Optional existing conversation UUID to attach to")
    enable_wake_word: bool = Field(default=False, description="Whether to request opt-in wake-word listening")


class VoiceSessionResponse(BaseModel):
    """Voice session metadata and current state."""
    session_id: str
    user_id: str
    conversation_id: Optional[str] = None
    state: VoiceSessionState
    wake_word_active: bool = False
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class VoiceChatResponse(BaseModel):
    """End-to-end voice conversational turn response."""
    session_id: Optional[str] = None
    conversation_id: str
    user_text: str
    transcription: TranscriptionResult
    assistant_text: str
    synthesis: Optional[SynthesisResult] = None
    approval_required: bool = False
    pending_action_id: Optional[str] = None
    model_used: str
    latency_ms: float


class VoiceStatusResponse(BaseModel):
    """Comprehensive voice subsystem health, providers, and hardware status."""
    is_enabled: bool
    local_only_mode: bool
    stt: Dict[str, Any]
    tts: Dict[str, Any]
    wake_word: WakeWordStatus
    personality: VoiceProfile
    hardware: Dict[str, Any]
