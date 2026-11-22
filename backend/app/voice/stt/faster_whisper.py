"""
Faster-Whisper Speech-To-Text Adapter for LOVE (Phase 06).
Optimized for NVIDIA GTX 1650 4GB VRAM and CPU fallback with int8 quantization.
"""

import asyncio
import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.audio import convert_to_wav_16k_mono, detect_audio_format, validate_audio_payload
from backend.app.voice.exceptions import STTError, STTProviderNotConfiguredError
from backend.app.voice.schemas import TranscriptionResult, TranscriptionSegment
from backend.app.voice.stt.base import BaseSTTProvider

try:
    from faster_whisper import WhisperModel
    _FASTER_WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    _FASTER_WHISPER_AVAILABLE = False


class FasterWhisperSTTProvider(BaseSTTProvider):
    """
    On-device Speech-To-Text adapter using CTranslate2 and Faster-Whisper.
    Enforces hardware bounds for GTX 1650 4GB (prefers base/small with int8/float16).
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        settings = get_settings()
        self._model_size = model_size or settings.VOICE_WHISPER_MODEL
        self._device_setting = device or settings.VOICE_WHISPER_DEVICE
        self._compute_type_setting = compute_type or settings.VOICE_WHISPER_COMPUTE_TYPE
        self._model: Optional[Any] = None
        self._resolved_device: Optional[str] = None
        self._resolved_compute_type: Optional[str] = None

    @property
    def provider_id(self) -> str:
        return "faster_whisper"

    @property
    def name(self) -> str:
        return "Faster-Whisper (CTranslate2 Local STT)"

    @property
    def is_local(self) -> bool:
        return True

    def _resolve_hardware(self) -> tuple[str, str]:
        """Resolves target compute device and quantization based on host GPU capacity."""
        if self._resolved_device and self._resolved_compute_type:
            return self._resolved_device, self._resolved_compute_type

        # Device determination
        if self._device_setting.lower() == "cuda":
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        elif self._device_setting.lower() == "cpu":
            dev = "cpu"
        else:  # auto
            # Use CUDA if available on GTX 1650
            dev = "cuda" if torch.cuda.is_available() else "cpu"

        # Compute type determination
        if dev == "cuda":
            # GTX 1650 (Turing TU117) has 4GB VRAM. int8 or float16 are recommended.
            comp = self._compute_type_setting if self._compute_type_setting in ("float16", "int8", "int8_float16") else "int8"
        else:
            comp = "int8" if self._compute_type_setting in ("int8", "auto") else "int8"

        self._resolved_device = dev
        self._resolved_compute_type = comp
        return dev, comp

    def _find_local_model_path(self) -> Optional[str]:
        """Checks whether the model exists in local project directory or HF cache."""
        # Check models/whisper/<model_size>
        local_dir = Path("models") / "whisper" / self._model_size
        if local_dir.exists() and any(local_dir.iterdir()):
            return str(local_dir)

        # Check HuggingFace hub cache
        hf_cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
        if hf_cache.exists():
            for item in hf_cache.glob(f"*whisper-{self._model_size}*"):
                if item.is_dir():
                    return str(item)

        return None

    def is_configured(self) -> bool:
        """Returns True if faster-whisper is installed."""
        return _FASTER_WHISPER_AVAILABLE

    async def is_available(self) -> bool:
        """
        Accurately checks if the model is locally downloaded and ready to execute.
        Strictly prevents automatic background model downloads.
        """
        if not self.is_configured():
            return False

        # If already loaded in memory
        if self._model is not None:
            return True

        # Check if local model weights are present
        model_path = self._find_local_model_path()
        return model_path is not None

    def _load_model(self) -> Any:
        """Loads WhisperModel instance into memory. Must be called in worker thread."""
        if self._model is not None:
            return self._model

        if not _FASTER_WHISPER_AVAILABLE:
            raise STTProviderNotConfiguredError(
                self.provider_id, "faster-whisper library is not installed."
            )

        model_path = self._find_local_model_path()
        if not model_path:
            raise STTProviderNotConfiguredError(
                self.provider_id,
                f"Model '{self._model_size}' is not downloaded locally. "
                "Automatic downloading is disabled to respect disk & network limits. "
                f"Please place model in models/whisper/{self._model_size} or run download script."
            )

        device, compute_type = self._resolve_hardware()
        logger.info(
            f"Loading Faster-Whisper model from '{model_path}' on device={device}, compute_type={compute_type}"
        )
        try:
            self._model = WhisperModel(
                model_path,
                device=device,
                compute_type=compute_type,
                download_root=None,
                local_files_only=True,
            )
            return self._model
        except Exception as exc:
            logger.error(f"Failed to load Faster-Whisper model: {exc}")
            # Fallback to CPU if CUDA fails
            if device == "cuda":
                logger.warning("Attempting CPU fallback for Faster-Whisper...")
                self._model = WhisperModel(
                    model_path,
                    device="cpu",
                    compute_type="int8",
                    download_root=None,
                    local_files_only=True,
                )
                self._resolved_device = "cpu"
                self._resolved_compute_type = "int8"
                return self._model
            raise STTError(self.provider_id, f"Model initialization failed: {exc}") from exc

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> TranscriptionResult:
        """
        Transcribes audio bytes asynchronously with timeout and Indian English prompt conditioning.
        """
        settings = get_settings()
        effective_timeout = timeout or settings.VOICE_STT_TIMEOUT_SECONDS
        target_lang = language or settings.VOICE_WHISPER_LANGUAGE

        # 1. Validate and convert audio to 16kHz mono WAV
        detected_fmt, duration = validate_audio_payload(audio_bytes)
        normalized_wav = convert_to_wav_16k_mono(audio_bytes, detected_fmt)

        # 2. Check model availability
        if not await self.is_available():
            raise STTProviderNotConfiguredError(
                self.provider_id,
                f"Faster-Whisper model '{self._model_size}' is not downloaded locally."
            )

        # 3. Synchronous transcription function for thread pool
        def _sync_transcribe() -> TranscriptionResult:
            model = self._load_model()
            wav_bio = io.BytesIO(normalized_wav)

            # Indian English prompt conditioning
            initial_prompt = (
                "Indian English pronunciation, technical terminology, clean conversational speech for LOVE AI assistant."
            )

            segments_iter, info = model.transcribe(
                wav_bio,
                language=target_lang if target_lang != "auto" else None,
                initial_prompt=initial_prompt,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
            )

            segments_list: List[TranscriptionSegment] = []
            aggregated_text = []

            for seg in segments_iter:
                text_clean = seg.text.strip()
                if text_clean:
                    aggregated_text.append(text_clean)
                    segments_list.append(
                        TranscriptionSegment(
                            start_time=round(seg.start, 2),
                            end_time=round(seg.end, 2),
                            text=text_clean,
                            confidence=round(seg.avg_logprob, 3) if hasattr(seg, "avg_logprob") else None,
                        )
                    )

            full_text = " ".join(aggregated_text).strip()
            return TranscriptionResult(
                text=full_text,
                language=info.language or target_lang,
                language_probability=round(info.language_probability, 3) if hasattr(info, "language_probability") else 1.0,
                duration_seconds=round(duration, 2),
                segments=segments_list,
                provider=self.provider_id,
                model=self._model_size,
            )

        # 4. Execute in worker thread with strict timeout
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_sync_transcribe),
                timeout=effective_timeout,
            )
            return result
        except asyncio.TimeoutError as exc:
            raise STTError(
                self.provider_id,
                f"Transcription exceeded timeout ceiling of {effective_timeout}s."
            ) from exc
        except Exception as exc:
            if isinstance(exc, (STTError, STTProviderNotConfiguredError)):
                raise
            raise STTError(self.provider_id, f"Transcription runtime failure: {exc}") from exc

    def get_model_info(self) -> Dict[str, Any]:
        dev, comp = self._resolve_hardware()
        model_path = self._find_local_model_path()
        return {
            "provider": self.provider_id,
            "model_size": self._model_size,
            "device": dev,
            "compute_type": comp,
            "model_path": model_path,
            "is_loaded": self._model is not None,
            "is_available": model_path is not None,
        }
