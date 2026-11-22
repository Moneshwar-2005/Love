"""
Mock Wake-Word Detector for testing and offline verification (Phase 06).
"""

from typing import Tuple
from backend.app.voice.schemas import WakeWordStatus
from backend.app.voice.wake_word.base import BaseWakeWordDetector


class MockWakeWordDetector(BaseWakeWordDetector):
    """
    Mock wake-word detector enabling full verification of state transitions,
    permission controls, and audio pipeline triggering without model files.
    """

    def __init__(self, threshold: float = 0.5):
        self._threshold = threshold
        self._is_active = False
        self._mic_permission_granted = False
        self._force_detected = False
        self._model_available = True

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def target_phrase(self) -> str:
        return "Hey LOVE"

    def is_configured(self) -> bool:
        return True

    def is_model_available(self) -> bool:
        return self._model_available

    def set_model_available(self, available: bool) -> None:
        self._model_available = available

    def set_force_detected(self, detected: bool) -> None:
        self._force_detected = detected

    def get_status(self) -> WakeWordStatus:
        if not self._model_available:
            msg = "Custom wake-word model not available (Mock mode)."
        elif not self._mic_permission_granted:
            msg = "Microphone access requires explicit user permission."
        elif not self._is_active:
            msg = "Wake-word detection is inactive."
        else:
            msg = "Mock wake-word detection is actively monitoring."

        return WakeWordStatus(
            is_enabled=True,
            is_active=self._is_active,
            provider=self.provider_id,
            target_phrase=self.target_phrase,
            threshold=self._threshold,
            model_available=self._model_available,
            model_path="mock/models/wakeword/hey_love.onnx",
            mic_permission_granted=self._mic_permission_granted,
            message=msg,
        )

    def set_active(self, active: bool, mic_permission: bool = False) -> WakeWordStatus:
        if active:
            if not self._model_available:
                from backend.app.voice.exceptions import WakeWordModelNotFoundError
                raise WakeWordModelNotFoundError(self.target_phrase, "mock/hey_love.onnx")
            if not mic_permission and not self._mic_permission_granted:
                from backend.app.voice.exceptions import WakeWordError
                raise WakeWordError("Microphone permission required.")
            self._mic_permission_granted = True
            self._is_active = True
        else:
            self._is_active = False

        return self.get_status()

    def detect_in_audio(self, audio_bytes: bytes) -> Tuple[bool, float]:
        if self._force_detected:
            return True, 0.95
        return False, 0.05
