"""
Piper Local Text-To-Speech Provider (Phase 06).
Fast, privacy-preserving, local on-device VITS speech synthesizer.
"""

import asyncio
import base64
import shutil
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.audio import validate_audio_payload
from backend.app.voice.exceptions import TTSError, TTSProviderNotConfiguredError
from backend.app.voice.personality import PROVIDER_VOICE_CATALOGS, get_active_voice_profile
from backend.app.voice.schemas import SynthesisResult, VoiceProfile
from backend.app.voice.tts.base import BaseTTSProvider


class PiperTTSProvider(BaseTTSProvider):
    """
    On-device Piper TTS synthesizer.
    Runs locally without internet access or GPU overhead.
    """

    def __init__(
        self,
        binary_path: Optional[str] = None,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        settings = get_settings()
        self._binary_path = binary_path or settings.VOICE_PIPER_BINARY_PATH or shutil.which("piper")
        self._model_path = model_path or settings.VOICE_PIPER_MODEL_PATH
        self._config_path = config_path or settings.VOICE_PIPER_CONFIG_PATH

    @property
    def provider_id(self) -> str:
        return "piper"

    @property
    def name(self) -> str:
        return "Piper (On-Device Neural VITS Local TTS)"

    @property
    def is_local(self) -> bool:
        return True

    def _resolve_model_file(self) -> Optional[Path]:
        """Checks configured path or models/piper/ for Indian English ONNX voice models."""
        if self._model_path and Path(self._model_path).exists():
            return Path(self._model_path)

        local_dir = Path("models") / "piper"
        if local_dir.exists():
            for p in local_dir.glob("*.onnx"):
                if p.is_file():
                    return p
        return None

    def is_configured(self) -> bool:
        """Returns True only if both the piper executable and model file exist locally."""
        bin_ok = bool(self._binary_path and Path(self._binary_path).exists())
        model_ok = self._resolve_model_file() is not None
        return bin_ok and model_ok

    async def is_available(self) -> bool:
        """Accurately checks readiness without downloading models."""
        return self.is_configured()

    async def list_voices(self) -> List[Dict[str, Any]]:
        return PROVIDER_VOICE_CATALOGS.get("piper", [])

    async def synthesize(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        voice_id: Optional[str] = None,
    ) -> SynthesisResult:
        if not self.is_configured():
            raise TTSProviderNotConfiguredError(
                self.provider_id,
                "Piper binary or voice model (.onnx) is not found. "
                "Automated model downloads are disabled. Please configure VOICE_PIPER_BINARY_PATH and VOICE_PIPER_MODEL_PATH."
            )

        model_file = self._resolve_model_file()
        prof = profile or get_active_voice_profile()
        target_voice = voice_id or prof.provider_voice_map.get("piper", "en_IN-cmu_indic-medium")

        cmd = [
            str(self._binary_path),
            "--model", str(model_file),
            "--output_file", "-",  # output wav to stdout
        ]
        if self._config_path and Path(self._config_path).exists():
            cmd.extend(["--config", str(self._config_path)])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=text.encode("utf-8"))

            if process.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace")[:200]
                raise TTSError(self.provider_id, f"Piper exited with code {process.returncode}: {err_text}")

            audio_data = stdout
            _, duration = validate_audio_payload(audio_data)

            return SynthesisResult(
                audio_bytes=audio_data,
                audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                format="audio/wav",
                duration_seconds=round(duration, 2),
                sample_rate=22050,
                provider=self.provider_id,
                voice_id=target_voice,
                character_count=len(text),
            )
        except Exception as exc:
            if isinstance(exc, (TTSError, TTSProviderNotConfiguredError)):
                raise
            raise TTSError(self.provider_id, f"Piper execution error: {exc}") from exc

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
