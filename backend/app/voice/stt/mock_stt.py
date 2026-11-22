"""
Mock Speech-To-Text Provider for testing and offline environments (Phase 06).
"""

from typing import Any, Dict, List, Optional
from backend.app.voice.audio import validate_audio_payload
from backend.app.voice.schemas import TranscriptionResult, TranscriptionSegment
from backend.app.voice.stt.base import BaseSTTProvider


class MockSTTProvider(BaseSTTProvider):
    """
    Deterministic STT provider for automated test suites and offline verification.
    """

    def __init__(self, predefined_text: Optional[str] = None):
        self._predefined_text = predefined_text
        self._is_available = True

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def name(self) -> str:
        return "Mock Local STT Runtime"

    @property
    def is_local(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return True

    async def is_available(self) -> bool:
        return self._is_available

    def set_availability(self, available: bool) -> None:
        self._is_available = available

    def set_text(self, text: str) -> None:
        self._predefined_text = text

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> TranscriptionResult:
        # Validate audio first
        detected_fmt, duration = validate_audio_payload(audio_bytes)

        text = self._predefined_text or "Hello LOVE, what is the weather today?"
        words = text.split()
        segments: List[TranscriptionSegment] = []

        if words:
            seg_duration = duration / len(words)
            for i, word in enumerate(words):
                segments.append(
                    TranscriptionSegment(
                        start_time=round(i * seg_duration, 2),
                        end_time=round((i + 1) * seg_duration, 2),
                        text=word,
                        confidence=0.98,
                    )
                )
        else:
            segments.append(
                TranscriptionSegment(
                    start_time=0.0,
                    end_time=duration,
                    text=text,
                    confidence=0.98,
                )
            )

        return TranscriptionResult(
            text=text,
            language=language or "en",
            language_probability=0.99,
            duration_seconds=round(duration, 2),
            segments=segments,
            provider=self.provider_id,
            model="mock_stt_v1",
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_id,
            "model_size": "mock",
            "device": "cpu",
            "compute_type": "int8",
            "is_loaded": True,
            "is_available": True,
        }
