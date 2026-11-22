"""
Voice Session Management and State Machine (Phase 06).
Enforces single-active-session per user to eliminate crosstalk, race conditions, and runaway audio generation.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.app.core.logging import logger
from backend.app.voice.exceptions import VoiceSessionError
from backend.app.voice.schemas import VoiceSessionResponse, VoiceSessionState


# Allowed State Transitions
VALID_TRANSITIONS = {
    VoiceSessionState.IDLE: {
        VoiceSessionState.LISTENING,
        VoiceSessionState.RECORDING,
        VoiceSessionState.CANCELLED,
    },
    VoiceSessionState.LISTENING: {
        VoiceSessionState.RECORDING,
        VoiceSessionState.IDLE,
        VoiceSessionState.CANCELLED,
        VoiceSessionState.ERROR,
    },
    VoiceSessionState.RECORDING: {
        VoiceSessionState.TRANSCRIBING,
        VoiceSessionState.CANCELLED,
        VoiceSessionState.ERROR,
    },
    VoiceSessionState.TRANSCRIBING: {
        VoiceSessionState.THINKING,
        VoiceSessionState.IDLE,
        VoiceSessionState.CANCELLED,
        VoiceSessionState.ERROR,
    },
    VoiceSessionState.THINKING: {
        VoiceSessionState.SPEAKING,
        VoiceSessionState.IDLE,
        VoiceSessionState.CANCELLED,
        VoiceSessionState.ERROR,
    },
    VoiceSessionState.SPEAKING: {
        VoiceSessionState.IDLE,
        VoiceSessionState.LISTENING,
        VoiceSessionState.CANCELLED,
        VoiceSessionState.ERROR,
    },
    VoiceSessionState.PAUSED: {
        VoiceSessionState.LISTENING,
        VoiceSessionState.IDLE,
        VoiceSessionState.CANCELLED,
    },
    VoiceSessionState.CANCELLED: {VoiceSessionState.IDLE},
    VoiceSessionState.ERROR: {VoiceSessionState.IDLE},
}


class VoiceSession:
    """Represents a discrete voice dialogue interaction lifecycle."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        enable_wake_word: bool = False,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.state = VoiceSessionState.IDLE
        self.wake_word_active = enable_wake_word
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.error_message: Optional[str] = None
        self.active_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def transition_to(self, new_state: VoiceSessionState, error: Optional[str] = None) -> None:
        """Enforces legal state transitions according to the state machine."""
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed and new_state != self.state:
            raise VoiceSessionError(
                f"Illegal voice session transition from '{self.state.value}' to '{new_state.value}'.",
                status_code=400,
            )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        if error:
            self.error_message = error

    def cancel(self) -> None:
        """Immediately interrupts any in-flight task and transitions to CANCELLED."""
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            logger.info(f"Active audio task cancelled for session '{self.session_id}'.")
        self.state = VoiceSessionState.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def to_response(self) -> VoiceSessionResponse:
        return VoiceSessionResponse(
            session_id=self.session_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            state=self.state,
            wake_word_active=self.wake_word_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            error_message=self.error_message,
        )


class VoiceSessionManager:
    """
    Manages active voice sessions and enforces user concurrency constraints.
    """

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}
        self._user_active_session: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        enable_wake_word: bool = False,
    ) -> VoiceSession:
        """
        Creates a new voice session for the user.
        Rejects creation if another active recording/processing session exists for this user.
        """
        async with self._lock:
            existing_id = self._user_active_session.get(user_id)
            if existing_id and existing_id in self._sessions:
                existing_session = self._sessions[existing_id]
                # If existing session is in active processing, reject concurrent session
                if existing_session.state in (
                    VoiceSessionState.RECORDING,
                    VoiceSessionState.TRANSCRIBING,
                    VoiceSessionState.THINKING,
                    VoiceSessionState.SPEAKING,
                ):
                    raise VoiceSessionError(
                        f"Active voice session '{existing_id}' is currently in state '{existing_session.state.value}'. "
                        "Please complete or cancel the existing session before starting a new one.",
                        status_code=409,
                    )

            session_id = str(uuid.uuid4())
            session = VoiceSession(
                session_id=session_id,
                user_id=user_id,
                conversation_id=conversation_id,
                enable_wake_word=enable_wake_word,
            )
            self._sessions[session_id] = session
            self._user_active_session[user_id] = session_id
            return session

    async def get_session(self, session_id: str, user_id: str) -> VoiceSession:
        """Retrieves session verifying user authorization."""
        session = self._sessions.get(session_id)
        if not session or session.user_id != user_id:
            raise VoiceSessionError(f"Voice session '{session_id}' not found or access denied.", status_code=404)
        return session

    async def cancel_session(self, session_id: str, user_id: str) -> VoiceSession:
        """Cancels session and releases user concurrency lock."""
        session = await self.get_session(session_id, user_id)
        session.cancel()
        async with self._lock:
            if self._user_active_session.get(user_id) == session_id:
                self._user_active_session.pop(user_id, None)
        return session

    async def end_session(self, session_id: str, user_id: str) -> None:
        """Ends an idle or completed session."""
        session = await self.get_session(session_id, user_id)
        session.state = VoiceSessionState.IDLE
        async with self._lock:
            if self._user_active_session.get(user_id) == session_id:
                self._user_active_session.pop(user_id, None)

    async def cleanup_expired_sessions(self, ttl_seconds: int = 3600) -> int:
        """Removes sessions older than TTL."""
        now = datetime.now(timezone.utc)
        count = 0
        async with self._lock:
            to_remove = []
            for sid, s in self._sessions.items():
                age = (now - s.updated_at).total_seconds()
                if age > ttl_seconds and s.state in (VoiceSessionState.IDLE, VoiceSessionState.CANCELLED, VoiceSessionState.ERROR):
                    to_remove.append(sid)

            for sid in to_remove:
                s = self._sessions.pop(sid)
                if self._user_active_session.get(s.user_id) == sid:
                    self._user_active_session.pop(s.user_id, None)
                count += 1
        return count


_global_session_manager: Optional[VoiceSessionManager] = None


def get_voice_session_manager() -> VoiceSessionManager:
    """Singleton getter for VoiceSessionManager."""
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = VoiceSessionManager()
    return _global_session_manager
