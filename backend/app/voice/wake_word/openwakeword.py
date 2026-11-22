"""
openWakeWord Acoustic Detection Adapter for 'Hey LOVE' (Phase 06).
Strictly verifies custom model presence; does NOT substitute unrelated wake words.
"""

from pathlib import Path
from typing import Any, Optional, Tuple
import numpy as np

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.audio import convert_to_wav_16k_mono, detect_audio_format, validate_audio_payload
from backend.app.voice.exceptions import WakeWordError, WakeWordModelNotFoundError
from backend.app.voice.schemas import WakeWordStatus
from backend.app.voice.wake_word.base import BaseWakeWordDetector

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    _OPENWAKEWORD_AVAILABLE = True
except ImportError:
    openwakeword = None
    OWWModel = None
    _OPENWAKEWORD_AVAILABLE = False


class OpenWakeWordDetector(BaseWakeWordDetector):
    """
    openWakeWord adapter for the phrase 'Hey LOVE'.
    Requires a dedicated trained model ('hey_love.onnx') in 'models/wakeword/'.
    """

    DEFAULT_MODEL_DIR = Path("models") / "wakeword"
    CUSTOM_MODEL_FILENAME = "hey_love.onnx"

    def __init__(self, threshold: Optional[float] = None):
        settings = get_settings()
        self._threshold = threshold if threshold is not None else settings.VOICE_WAKE_WORD_THRESHOLD
        self._is_enabled_setting = settings.VOICE_WAKE_WORD_ENABLED
        self._is_active = False
        self._mic_permission_granted = False
        self._model_instance: Optional[Any] = None

    @property
    def provider_id(self) -> str:
        return "openwakeword"

    @property
    def target_phrase(self) -> str:
        return "Hey LOVE"

    def is_configured(self) -> bool:
        return _OPENWAKEWORD_AVAILABLE

    def _get_custom_model_path(self) -> Optional[Path]:
        """Checks for the custom 'hey_love.onnx' or 'hey_love.tflite' model file."""
        candidates = [
            self.DEFAULT_MODEL_DIR / self.CUSTOM_MODEL_FILENAME,
            self.DEFAULT_MODEL_DIR / "hey_love.tflite",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    def is_model_available(self) -> bool:
        """Returns True if the custom 'Hey LOVE' model exists locally."""
        return self._get_custom_model_path() is not None

    def get_status(self) -> WakeWordStatus:
        """Accurately reports wake-word readiness and training requirements."""
        model_path = self._get_custom_model_path()
        model_available = model_path is not None

        if not self.is_configured():
            msg = "openWakeWord library is not installed."
        elif not model_available:
            msg = (
                "Custom acoustic model for 'Hey LOVE' ('hey_love.onnx') is not present in models/wakeword/. "
                "Default openWakeWord models (alexa, hey_jarvis, etc.) do not support 'Hey LOVE'. "
                "Train or place custom model in models/wakeword/hey_love.onnx to enable wake-word detection."
            )
        elif not self._mic_permission_granted:
            msg = "Model is available. Microphone access requires explicit user permission."
        elif not self._is_active:
            msg = "Model is ready. Wake-word detection is currently inactive (opt-in)."
        else:
            msg = "Wake-word detection is active and listening for 'Hey LOVE'."

        return WakeWordStatus(
            is_enabled=self._is_enabled_setting,
            is_active=self._is_active,
            provider=self.provider_id,
            target_phrase=self.target_phrase,
            threshold=self._threshold,
            model_available=model_available,
            model_path=str(model_path) if model_path else None,
            mic_permission_granted=self._mic_permission_granted,
            message=msg,
        )

    def set_active(self, active: bool, mic_permission: bool = False) -> WakeWordStatus:
        """
        Activates or deactivates listening.
        Activation requires both model availability and explicit microphone permission.
        """
        if active:
            if not self.is_model_available():
                expected_path = str(self.DEFAULT_MODEL_DIR / self.CUSTOM_MODEL_FILENAME)
                raise WakeWordModelNotFoundError(self.target_phrase, expected_path)
            if not mic_permission and not self._mic_permission_granted:
                raise WakeWordError(
                    "Cannot activate wake-word listening without explicit microphone permission from user."
                )
            self._mic_permission_granted = True
            self._is_active = True
            self._ensure_model_loaded()
            logger.info("Wake-word monitoring activated for 'Hey LOVE'.")
        else:
            self._is_active = False
            logger.info("Wake-word monitoring deactivated.")

        return self.get_status()

    def _ensure_model_loaded(self) -> None:
        """Loads custom wake-word model into memory."""
        if self._model_instance is not None:
            return

        model_path = self._get_custom_model_path()
        if not model_path:
            raise WakeWordModelNotFoundError(self.target_phrase, str(self.DEFAULT_MODEL_DIR / self.CUSTOM_MODEL_FILENAME))

        try:
            self._model_instance = OWWModel(
                wakeword_models=[str(model_path)],
                inference_framework="onnx",
            )
        except Exception as exc:
            raise WakeWordError(f"Failed to load openWakeWord model from '{model_path}': {exc}") from exc

    def detect_in_audio(self, audio_bytes: bytes) -> Tuple[bool, float]:
        """
        Runs inference on audio buffer to detect 'Hey LOVE'.
        Returns: (detected: bool, confidence: float)
        """
        if not self.is_model_available():
            raise WakeWordModelNotFoundError(self.target_phrase, str(self.DEFAULT_MODEL_DIR / self.CUSTOM_MODEL_FILENAME))

        self._ensure_model_loaded()

        # Validate and convert audio to 16kHz mono WAV
        fmt, _ = validate_audio_payload(audio_bytes)
        wav_bytes = convert_to_wav_16k_mono(audio_bytes, fmt)

        # Convert WAV bytes to 16-bit PCM numpy array
        # Header is 44 bytes in standard WAV
        pcm_data = np.frombuffer(wav_bytes[44:], dtype=np.int16)
        if len(pcm_data) < 1280:  # openWakeWord expects 1280 sample chunks (80ms at 16kHz)
            return False, 0.0

        # Feed chunks through model
        max_score = 0.0
        step = 1280
        for i in range(0, len(pcm_data) - step + 1, step):
            chunk = pcm_data[i : i + step]
            prediction = self._model_instance.predict(chunk)
            for model_name, score in prediction.items():
                if score > max_score:
                    max_score = float(score)

        detected = max_score >= self._threshold
        return detected, round(max_score, 4)
