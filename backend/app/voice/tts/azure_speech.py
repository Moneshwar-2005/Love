"""
Azure Speech Services Text-To-Speech Provider (Phase 06).
Primary cloud TTS provider with authentic Indian English neural voices (Neerja, Ananya).
"""

import base64
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.audio import validate_audio_payload
from backend.app.voice.exceptions import TTSError, TTSProviderNotConfiguredError, VoicePrivacyRestrictionError
from backend.app.voice.personality import PROVIDER_VOICE_CATALOGS, build_ssml, get_active_voice_profile
from backend.app.voice.schemas import SynthesisResult, VoiceProfile
from backend.app.voice.tts.base import BaseTTSProvider


class AzureSpeechTTSProvider(BaseTTSProvider):
    """
    Azure Cognitive Services Speech TTS Adapter.
    Supports SSML with prosody control, natural pauses, and Indian English female voices.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        default_voice: Optional[str] = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.VOICE_AZURE_SPEECH_KEY
        self._region = region or settings.VOICE_AZURE_SPEECH_REGION
        self._default_voice = default_voice or settings.VOICE_AZURE_VOICE_NAME

    @property
    def provider_id(self) -> str:
        return "azure"

    @property
    def name(self) -> str:
        return "Azure Speech Services (Cognitive Services Neural TTS)"

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        """Returns True only when both API key and Azure region are set."""
        return bool(self._api_key and self._region)

    async def is_available(self) -> bool:
        """Verifies configuration and endpoint reachability."""
        if not self.is_configured():
            return False
        settings = get_settings()
        if settings.LOCAL_ONLY_MODE:
            return False
        return True

    async def list_voices(self) -> List[Dict[str, Any]]:
        """Returns registered Indian English neural voices."""
        return PROVIDER_VOICE_CATALOGS.get("azure", [])

    def _get_endpoint_url(self) -> str:
        return f"https://{self._region}.tts.speech.microsoft.com/cognitiveservices/v1"

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
                self.provider_id, "VOICE_AZURE_SPEECH_KEY or VOICE_AZURE_SPEECH_REGION is missing."
            )

        prof = profile or get_active_voice_profile()
        target_voice = voice_id or prof.provider_voice_map.get("azure", self._default_voice)
        ssml_payload = build_ssml(text, prof, provider="azure")

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "LOVE-Personal-AI-Assistant",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self._get_endpoint_url(),
                    headers=headers,
                    content=ssml_payload.encode("utf-8"),
                )

                if response.status_code != 200:
                    err_msg = response.text[:200]
                    raise TTSError(
                        self.provider_id,
                        f"Azure API returned status {response.status_code}: {err_msg}",
                    )

                audio_data = response.content
                _, duration = validate_audio_payload(audio_data)

                return SynthesisResult(
                    audio_bytes=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                    format="audio/wav",
                    duration_seconds=round(duration, 2),
                    sample_rate=24000,
                    provider=self.provider_id,
                    voice_id=target_voice,
                    character_count=len(text),
                )
        except Exception as exc:
            if isinstance(exc, (TTSError, TTSProviderNotConfiguredError, VoicePrivacyRestrictionError)):
                raise
            raise TTSError(self.provider_id, f"Network or synthesis error: {exc}") from exc

    async def synthesize_stream(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        res = await self.synthesize(text, profile, voice_id)
        if res.audio_bytes:
            # Yield in 4KB chunks
            chunk_size = 4096
            for i in range(0, len(res.audio_bytes), chunk_size):
                yield res.audio_bytes[i : i + chunk_size]
