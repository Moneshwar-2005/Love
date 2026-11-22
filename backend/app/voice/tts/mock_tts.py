"""
Mock Text-To-Speech Provider for testing, local fallback, and offline verification (Phase 06).
"""

import base64
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.app.voice.audio import generate_synthetic_wav, validate_audio_payload
from backend.app.voice.personality import PROVIDER_VOICE_CATALOGS, get_active_voice_profile
from backend.app.voice.schemas import SynthesisResult, VoiceProfile
from backend.app.voice.tts.base import BaseTTSProvider


class MockTTSProvider(BaseTTSProvider):
    """
    Deterministic in-memory TTS synthesizer generating valid WAV audio.
    Used for unit tests, offline development, and safe test-suite execution.
    """

    def __init__(self, sample_rate: int = 16000):
        self._sample_rate = sample_rate
        self._is_available = True

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def name(self) -> str:
        return "Mock Local TTS Runtime"

    @property
    def is_local(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return True

    async def is_available(self) -> bool:
        return self._is_available

    def set_availability(self, available: bool) -> None:
        self._is_available = available

    async def list_voices(self) -> List[Dict[str, Any]]:
        return PROVIDER_VOICE_CATALOGS.get("mock", [])

    async def synthesize(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> SynthesisResult:
        prof = profile or get_active_voice_profile()
        target_voice = voice_id or prof.provider_voice_map.get("mock", "mock_love_female_in")

        # Estimate duration: ~150 words per minute -> 2.5 words/sec -> 0.4s per word
        words = text.split()
        duration = max(0.5, round(len(words) * 0.4, 2))

        # Generate valid PCM WAV audio (tone frequency 440Hz for voice simulated pitch)
        audio_bytes = generate_synthetic_wav(
            duration_seconds=duration,
            sample_rate=self._sample_rate,
            frequency=440.0,
            is_silence=False,
        )

        return SynthesisResult(
            audio_bytes=audio_bytes,
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            format="audio/wav",
            duration_seconds=duration,
            sample_rate=self._sample_rate,
            provider=self.provider_id,
            voice_id=target_voice,
            character_count=len(text),
        )

    async def synthesize_stream(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        res = await self.synthesize(text, profile, voice_id)
        if res.audio_bytes:
            chunk_size = 4096
            for i in range(0, len(res.audio_bytes), chunk_size):
                yield res.audio_bytes[i : i + chunk_size]
