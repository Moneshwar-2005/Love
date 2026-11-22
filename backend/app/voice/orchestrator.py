"""
Voice Orchestration Service (Phase 06).
Connects audio capture, STT, existing Intelligence Layer, Memory, Work Engine, and TTS.
"""

import base64
import time
from typing import Any, Dict, Optional
import torch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.database.models.user import User
from backend.app.intelligence.engine import get_intelligence_engine
from backend.app.intelligence.schemas import ChatRequest
from backend.app.voice.audio import cleanup_audio_temp_directory, validate_audio_payload
from backend.app.voice.exceptions import VoiceSessionError
from backend.app.voice.personality import get_active_voice_profile
from backend.app.voice.schemas import (
    SynthesisResult,
    TranscriptionResult,
    VoiceChatResponse,
    VoiceSessionState,
    VoiceStatusResponse,
)
from backend.app.voice.session import VoiceSession, get_voice_session_manager
from backend.app.voice.stt import get_stt_provider, list_stt_providers
from backend.app.voice.tts import get_tts_provider, list_tts_providers
from backend.app.voice.wake_word import get_wake_word_detector


class VoiceOrchestrationService:
    """
    Central orchestration coordinator for LOVE's voice interface.
    Preserves existing conversation state, memory retrieval, task execution,
    and strict human-in-the-loop approval invariants.
    """

    def __init__(self):
        self.settings = get_settings()
        self.session_manager = get_voice_session_manager()

    async def get_system_status(self) -> VoiceStatusResponse:
        """Assembles live status of STT, TTS, wake-word, personality, and hardware metrics."""
        stt = get_stt_provider()
        tts_list = await list_tts_providers()
        active_tts = await get_tts_provider()
        wake_word = get_wake_word_detector()
        personality = get_active_voice_profile()

        # Hardware metrics
        cuda_avail = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "N/A"
        vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1) if cuda_avail else 0.0
        vram_used_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1) if cuda_avail else 0.0

        hardware_profile = {
            "cuda_available": cuda_avail,
            "device_name": gpu_name,
            "vram_total_mb": vram_total_mb,
            "vram_allocated_mb": vram_used_mb,
            "recommended_stt_model": "base",
            "host_gpu_bound": "4GB VRAM (GTX 1650)",
            "cpu_fallback_supported": True,
        }

        return VoiceStatusResponse(
            is_enabled=self.settings.VOICE_ENABLED,
            local_only_mode=self.settings.LOCAL_ONLY_MODE,
            stt={
                "active_provider": stt.provider_id,
                "name": stt.name,
                "is_local": stt.is_local,
                "is_configured": stt.is_configured(),
                "is_available": await stt.is_available(),
                "model_info": stt.get_model_info(),
                "available_providers": list_stt_providers(),
            },
            tts={
                "active_provider": active_tts.provider_id,
                "name": active_tts.name,
                "is_local": active_tts.is_local,
                "is_configured": active_tts.is_configured(),
                "is_available": await active_tts.is_available(),
                "all_providers": tts_list,
            },
            wake_word=wake_word.get_status(),
            personality=personality,
            hardware=hardware_profile,
        )

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        language: Optional[str] = None,
        provider_id: Optional[str] = None,
    ) -> TranscriptionResult:
        """Validates and transcribes raw audio bytes."""
        validate_audio_payload(audio_bytes, filename=filename)
        stt = get_stt_provider(provider_id)
        try:
            result = await stt.transcribe(audio_bytes, language=language)
            return result
        finally:
            if not self.settings.VOICE_RETAIN_AUDIO:
                cleanup_audio_temp_directory()

    async def synthesize_speech(
        self,
        text: str,
        provider_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        profile_id: Optional[str] = None,
    ) -> SynthesisResult:
        """Synthesizes text into audio using the resolved TTS provider."""
        tts = await get_tts_provider(provider_id)
        profile = get_active_voice_profile(profile_id)
        return await tts.synthesize(text, profile=profile, voice_id=voice_id)

    async def process_voice_turn(
        self,
        db: AsyncSession,
        user: User,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        filename: Optional[str] = None,
        stt_provider_id: Optional[str] = None,
        tts_provider_id: Optional[str] = None,
        profile_id: Optional[str] = None,
    ) -> VoiceChatResponse:
        """
        Executes a complete voice conversational turn:
        Audio Input -> STT -> Existing Intelligence Layer -> Memory & Work Tools -> TTS -> Voice Output.
        """
        start_time = time.perf_counter()
        session: Optional[VoiceSession] = None

        if session_id:
            session = await self.session_manager.get_session(session_id, user.id)
            session.transition_to(VoiceSessionState.RECORDING)
            session.transition_to(VoiceSessionState.TRANSCRIBING)

        # 1. Speech-to-Text Transcription
        transcription = await self.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            provider_id=stt_provider_id,
        )

        user_text = transcription.text.strip()
        if not user_text:
            user_text = "[Unintelligible speech]"

        if session:
            session.transition_to(VoiceSessionState.THINKING)

        # 2. Connect to Existing Intelligence Engine
        engine = get_intelligence_engine()
        chat_request = ChatRequest(
            message=user_text,
            conversation_id=conversation_id or (session.conversation_id if session else None),
        )

        conv, user_msg, assistant_msg, assistant_response = await engine.orchestrator.execute_chat(
            db=db,
            user=user,
            request=chat_request,
        )

        # Update session's active conversation if newly created
        if session and not session.conversation_id:
            session.conversation_id = conv.id

        assistant_text = assistant_response.content

        # 3. Check for Approval Requirement (HITL Invariant)
        approval_required = False
        pending_action_id = None

        if "requires your confirmation or approval" in assistant_text:
            approval_required = True
            # Verbal delivery adaptation: keep spoken prompt calm, clear, and reassuring
            spoken_text = (
                "I have planned this task, but it modifies your workspace and requires your explicit approval. "
                "Please review and approve the pending action in your LOVE interface to continue."
            )
        else:
            spoken_text = assistant_text

        if session:
            session.transition_to(VoiceSessionState.SPEAKING)

        # 4. Text-To-Speech Synthesis
        synthesis: Optional[SynthesisResult] = None
        try:
            synthesis = await self.synthesize_speech(
                text=spoken_text,
                provider_id=tts_provider_id,
                profile_id=profile_id,
            )
        except Exception as exc:
            logger.error(f"Voice synthesis failed during turn: {exc}")
            # Non-blocking: return conversational text even if audio synthesis fails

        if session:
            session.transition_to(VoiceSessionState.IDLE)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return VoiceChatResponse(
            session_id=session.session_id if session else None,
            conversation_id=conv.id,
            user_text=user_text,
            transcription=transcription,
            assistant_text=assistant_text,
            synthesis=synthesis,
            approval_required=approval_required,
            pending_action_id=pending_action_id,
            model_used=assistant_response.model,
            latency_ms=round(duration_ms, 2),
        )


_global_voice_service: Optional[VoiceOrchestrationService] = None


def get_voice_service() -> VoiceOrchestrationService:
    """Singleton getter for VoiceOrchestrationService."""
    global _global_voice_service
    if _global_voice_service is None:
        _global_voice_service = VoiceOrchestrationService()
    return _global_voice_service
