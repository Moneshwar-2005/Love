"""
Voice Engine, Speech Recognition & Wake Word Endpoints (Phase 06).
Provides authenticated endpoints for speech-to-text, text-to-speech,
session lifecycle, wake-word controls, and voice chat interaction.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import get_current_active_user
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.voice.exceptions import (
    AudioValidationError,
    STTError,
    STTProviderNotConfiguredError,
    TTSError,
    TTSProviderNotConfiguredError,
    VoicePrivacyRestrictionError,
    VoiceSessionError,
    WakeWordError,
    WakeWordModelNotFoundError,
)
from backend.app.voice.orchestrator import VoiceOrchestrationService, get_voice_service
from backend.app.voice.personality import (
    PROVIDER_VOICE_CATALOGS,
    get_active_voice_profile,
    list_available_profiles,
)
from backend.app.voice.schemas import (
    SynthesisResult,
    TranscriptionResult,
    VoiceChatResponse,
    VoiceProfile,
    VoiceSessionCreateRequest,
    VoiceSessionResponse,
    VoiceStatusResponse,
    WakeWordStatus,
)
from backend.app.voice.session import get_voice_session_manager
from backend.app.voice.stt import list_stt_providers
from backend.app.voice.tts import list_tts_providers
from backend.app.voice.wake_word import get_wake_word_detector

router = APIRouter(prefix="/voice", tags=["Voice Engine & Speech"])


class SynthesizeRequest(BaseModel):
    """Payload to synthesize speech from text."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text content to speak")
    provider_id: Optional[str] = Field(None, description="Optional TTS provider (azure, elevenlabs, piper, mock)")
    voice_id: Optional[str] = Field(None, description="Optional voice identifier override")
    profile_id: Optional[str] = Field(None, description="Optional personality profile override")
    return_binary: bool = Field(False, description="Whether to return raw binary audio or JSON with Base64")


class WakeWordToggleRequest(BaseModel):
    """Payload to toggle wake-word monitoring."""
    active: bool = Field(..., description="Desired monitoring state")
    mic_permission_granted: bool = Field(False, description="Explicit user microphone permission grant")


# 1. Subsystem Status & Capabilities
@router.get(
    "/status",
    response_model=VoiceStatusResponse,
    summary="Get complete Voice Engine status",
    description="Returns configuration, providers, active personality, wake-word state, and hardware VRAM metrics.",
)
async def get_voice_status(
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> VoiceStatusResponse:
    return await service.get_system_status()


# 2. Provider Discovery
@router.get("/stt/providers", summary="List Speech-To-Text providers")
async def get_stt_providers(
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    return list_stt_providers()


@router.get("/tts/providers", summary="List Text-To-Speech providers")
async def get_tts_providers(
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    return await list_tts_providers()


@router.get("/tts/voices", summary="List available voices by provider")
async def get_tts_voices(
    provider: Optional[str] = Query(None, description="Filter by provider (azure, elevenlabs, piper, mock)"),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, List[Dict[str, Any]]]:
    if provider:
        return {provider: PROVIDER_VOICE_CATALOGS.get(provider.lower(), [])}
    return PROVIDER_VOICE_CATALOGS


@router.get("/profile", response_model=VoiceProfile, summary="Get active voice personality profile")
async def get_voice_personality(
    profile_id: Optional[str] = Query(None, description="Optional profile identifier"),
    current_user: User = Depends(get_current_active_user),
) -> VoiceProfile:
    return get_active_voice_profile(profile_id)


# 3. Session Management
@router.post(
    "/sessions",
    response_model=VoiceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new voice session",
    description="Initiates a single-user voice dialogue session, rejecting overlapping active speech sessions.",
)
async def create_voice_session(
    request: VoiceSessionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> VoiceSessionResponse:
    try:
        session = await service.session_manager.create_session(
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            enable_wake_word=request.enable_wake_word,
        )
        return session.to_response()
    except VoiceSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/sessions/{session_id}",
    response_model=VoiceSessionResponse,
    summary="Get voice session state",
)
async def get_voice_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> VoiceSessionResponse:
    try:
        session = await service.session_manager.get_session(session_id, current_user.id)
        return session.to_response()
    except VoiceSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=VoiceSessionResponse,
    summary="Cancel active voice session",
)
async def cancel_voice_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> VoiceSessionResponse:
    try:
        session = await service.session_manager.cancel_session(session_id, current_user.id)
        return session.to_response()
    except VoiceSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# 4. Transcription & Synthesis
@router.post(
    "/transcribe",
    response_model=TranscriptionResult,
    summary="Transcribe uploaded speech audio",
    description="Uploads an audio file (WAV, MP3, OGG, M4A, WEBM, FLAC) and transcribes it via faster-whisper.",
)
async def transcribe_audio_endpoint(
    file: UploadFile = File(..., description="Audio file binary upload"),
    language: Optional[str] = Form(None, description="Optional language code (e.g. 'en')"),
    provider_id: Optional[str] = Form(None, description="Optional STT provider override"),
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> TranscriptionResult:
    audio_bytes = await file.read()
    try:
        result = await service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename,
            language=language,
            provider_id=provider_id,
        )
        return result
    except AudioValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    except STTProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=exc.message)
    except STTError as exc:
        raise HTTPException(status_code=500, detail=exc.message)


@router.post(
    "/synthesize",
    summary="Synthesize speech from text",
    description="Generates speech audio using the active TTS provider (Azure, ElevenLabs, Piper, Mock).",
)
async def synthesize_speech_endpoint(
    request: SynthesizeRequest,
    current_user: User = Depends(get_current_active_user),
    service: VoiceOrchestrationService = Depends(get_voice_service),
):
    try:
        res = await service.synthesize_speech(
            text=request.text,
            provider_id=request.provider_id,
            voice_id=request.voice_id,
            profile_id=request.profile_id,
        )
        if request.return_binary:
            if not res.audio_bytes:
                raise HTTPException(status_code=500, detail="Synthesized audio bytes are empty.")
            return Response(content=res.audio_bytes, media_type=res.format)

        return res
    except VoicePrivacyRestrictionError as exc:
        raise HTTPException(status_code=403, detail=exc.message)
    except TTSProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=exc.message)
    except TTSError as exc:
        raise HTTPException(status_code=500, detail=exc.message)


# 5. Full End-to-End Voice Chat Turn
@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    summary="Full end-to-end voice conversational turn",
    description=(
        "Processes an audio utterance: Transcribes speech -> Routes through existing LOVE Intelligence "
        "Layer -> Retrieves persistent memory -> Runs work tools (requiring approval if medium/high risk) -> "
        "Synthesizes natural spoken response."
    ),
)
async def voice_chat_turn_endpoint(
    file: UploadFile = File(..., description="Recorded audio buffer"),
    session_id: Optional[str] = Form(None, description="Optional active voice session UUID"),
    conversation_id: Optional[str] = Form(None, description="Optional conversation UUID"),
    stt_provider_id: Optional[str] = Form(None, description="Optional STT provider override"),
    tts_provider_id: Optional[str] = Form(None, description="Optional TTS provider override"),
    profile_id: Optional[str] = Form(None, description="Optional voice personality profile override"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    service: VoiceOrchestrationService = Depends(get_voice_service),
) -> VoiceChatResponse:
    audio_bytes = await file.read()
    try:
        return await service.process_voice_turn(
            db=db,
            user=current_user,
            audio_bytes=audio_bytes,
            session_id=session_id,
            conversation_id=conversation_id,
            filename=file.filename,
            stt_provider_id=stt_provider_id,
            tts_provider_id=tts_provider_id,
            profile_id=profile_id,
        )
    except AudioValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    except STTProviderNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=exc.message)
    except VoiceSessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice interaction failure: {str(exc)}")


# 6. Wake-Word Controls
@router.get(
    "/wake-word/status",
    response_model=WakeWordStatus,
    summary="Get wake-word detection status and model readiness",
)
async def get_wake_word_status(
    current_user: User = Depends(get_current_active_user),
) -> WakeWordStatus:
    detector = get_wake_word_detector()
    return detector.get_status()


@router.post(
    "/wake-word/toggle",
    response_model=WakeWordStatus,
    summary="Toggle wake-word acoustic listening",
    description="Explicit opt-in control requiring user microphone permission. Refuses activation without custom model.",
)
async def toggle_wake_word(
    request: WakeWordToggleRequest,
    current_user: User = Depends(get_current_active_user),
) -> WakeWordStatus:
    detector = get_wake_word_detector()
    try:
        return detector.set_active(active=request.active, mic_permission=request.mic_permission_granted)
    except WakeWordModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
    except WakeWordError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
