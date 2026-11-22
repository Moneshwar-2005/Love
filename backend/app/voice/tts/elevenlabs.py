"""
ElevenLabs Text-To-Speech Provider (Phase 06).
Alternative cloud TTS provider for high-fidelity voice synthesis.
"""

import base64
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from backend.app.config.settings import get_settings
from backend.app.voice.audio import validate_audio_payload
from backend.app.voice.exceptions import TTSError, TTSProviderNotConfiguredError, VoicePrivacyRestrictionError
from backend.app.voice.personality import PROVIDER_VOICE_CATALOGS, get_active_voice_profile
from backend.app.voice.schemas import SynthesisResult, VoiceProfile
from backend.app.voice.tts.base import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):
    """
    ElevenLabs API Adapter for expressive voice synthesis.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.VOICE_ELEVENLABS_API_KEY
        self._voice_id = voice_id or settings.VOICE_ELEVENLABS_VOICE_ID

    @property
    def provider_id(self) -> str:
        return "elevenlabs"

    @property
    def name(self) -> str:
        return "ElevenLabs Neural TTS"

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(self._api_key and self._voice_id)

    async def is_available(self) -> bool:
        if not self.is_configured():
            return False
        settings = get_settings()
        if settings.LOCAL_ONLY_MODE:
            return False
        return True

    async def list_voices(self) -> List[Dict[str, Any]]:
        return PROVIDER_VOICE_CATALOGS.get("elevenlabs", [])

    async def synthesize(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> SynthesisResult:
        settings = get_settings()
        if settings.LOCAL_ONLY_MODE:
            raise VoicePrivacyRestrictionError(
                self.provider_id, "LOCAL_ONLY_MODE is enabled. Cloud synthesis is prohibited."
            )

        if not self.is_configured():
            raise TTSProviderNotConfiguredError(
                self.provider_id, "VOICE_ELEVENLABS_API_KEY or VOICE_ELEVENLABS_VOICE_ID is missing."
            )

        prof = profile or get_active_voice_profile()
        target_voice = voice_id or prof.provider_voice_map.get("elevenlabs", self._voice_id)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.65,
                "similarity_boost": 0.80,
                "style": 0.20,
                "use_speaker_boost": True,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    err_msg = response.text[:200]
                    raise TTSError(
                        self.provider_id,
                        f"ElevenLabs API returned status {response.status_code}: {err_msg}",
                    )

                audio_data = response.content
                _, duration = validate_audio_payload(audio_data)

                return SynthesisResult(
                    audio_bytes=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                    format="audio/mp3",
                    duration_seconds=round(duration, 2),
                    sample_rate=24000,
                    provider=self.provider_id,
                    voice_id=target_voice,
                    character_count=len(text),
                )
        except Exception as exc:
            if isinstance(exc, (TTSError, TTSProviderNotConfiguredError, VoicePrivacyRestrictionError)):
                raise
            raise TTSError(self.provider_id, f"ElevenLabs synthesis error: {exc}") from exc

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
