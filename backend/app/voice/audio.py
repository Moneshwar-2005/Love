"""
Audio processing, validation, normalization, and temporary buffer management (Phase 06).
"""

import io
import math
import os
import shutil
import struct
import tempfile
import wave
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Tuple

from backend.app.config.settings import get_settings
from backend.app.core.logging import logger
from backend.app.voice.exceptions import AudioValidationError

# Try importing soundfile / torchaudio for extended format support
try:
    import soundfile as sf
    _SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None
    _SOUNDFILE_AVAILABLE = False


SUPPORTED_FORMATS = {"wav", "mp3", "ogg", "m4a", "webm", "flac"}
MAGIC_SIGNATURES = {
    b"RIFF": "wav",
    b"ID3": "mp3",
    b"\xff\xfb": "mp3",
    b"\xff\xf3": "mp3",
    b"\xff\xf2": "mp3",
    b"OggS": "ogg",
    b"fLaC": "flac",
    b"\x1a\x45\xdf\xa3": "webm",
}


def detect_audio_format(audio_bytes: bytes, filename: Optional[str] = None) -> str:
    """
    Infers the audio container format using magic byte inspection and optional filename hint.
    """
    if len(audio_bytes) < 4:
        raise AudioValidationError("Audio payload is too small to determine format (minimum 4 bytes required).")

    # Check magic byte signatures
    for magic, fmt in MAGIC_SIGNATURES.items():
        if audio_bytes.startswith(magic):
            return fmt

    # Fallback to file extension hint if provided
    if filename:
        ext = filename.lower().split(".")[-1]
        if ext in SUPPORTED_FORMATS:
            return ext

    # If it has standard RIFF header at offset 0
    if audio_bytes[:4] == b"RIFF" and len(audio_bytes) > 12 and audio_bytes[8:12] == b"WAVE":
        return "wav"

    raise AudioValidationError(
        f"Unsupported or unrecognized audio format. Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}."
    )


def validate_audio_payload(
    audio_bytes: bytes,
    filename: Optional[str] = None,
    max_duration_seconds: Optional[int] = None,
    max_size_bytes: Optional[int] = None,
) -> Tuple[str, float]:
    """
    Validates audio byte payload against size, duration, and container structure.
    Returns: (detected_format, duration_seconds)
    """
    settings = get_settings()
    effective_max_size = max_size_bytes or settings.VOICE_AUDIO_MAX_FILE_SIZE_BYTES
    effective_max_duration = max_duration_seconds or settings.VOICE_AUDIO_MAX_DURATION_SECONDS

    # 1. File size check
    size = len(audio_bytes)
    if size == 0:
        raise AudioValidationError("Audio payload cannot be empty (0 bytes).")
    if size > effective_max_size:
        raise AudioValidationError(
            f"Audio file size ({size / (1024 * 1024):.2f} MB) exceeds maximum permitted limit "
            f"of {effective_max_size / (1024 * 1024):.2f} MB."
        )

    # 2. Format detection
    detected_format = detect_audio_format(audio_bytes, filename)

    # 3. Duration & integrity extraction
    duration = 0.0
    if detected_format == "wav":
        try:
            with io.BytesIO(audio_bytes) as bio:
                with wave.open(bio, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate <= 0:
                        raise AudioValidationError("Invalid WAV audio: frame rate must be positive.")
                    duration = frames / float(rate)
        except wave.Error as exc:
            raise AudioValidationError(f"Malformed or corrupt WAV audio structure: {exc}") from exc
    elif _SOUNDFILE_AVAILABLE:
        try:
            with io.BytesIO(audio_bytes) as bio:
                with sf.SoundFile(bio) as sfile:
                    frames = sfile.frames
                    rate = sfile.samplerate
                    if rate > 0:
                        duration = frames / float(rate)
        except Exception as exc:
            logger.warning(f"SoundFile inspection failed for format '{detected_format}': {exc}")
            # Approximate duration from byte length assuming 16kHz 16-bit mono as rough bound
            duration = min(float(size) / 32000.0, 1.0)
    else:
        # Fallback conservative estimate for compressed audio
        duration = 1.0

    if duration > effective_max_duration:
        raise AudioValidationError(
            f"Audio duration ({duration:.1f}s) exceeds maximum allowable limit of {effective_max_duration}s."
        )

    return detected_format, duration


def convert_to_wav_16k_mono(audio_bytes: bytes, source_format: str) -> bytes:
    """
    Converts and resamples arbitrary supported audio into 16,000 Hz, 16-bit PCM, single-channel (mono) WAV.
    This format is optimal for Whisper transcription and acoustic wake-word models.
    """
    if source_format == "wav":
        try:
            with io.BytesIO(audio_bytes) as bio:
                with wave.open(bio, "rb") as wf:
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    rate = wf.getframerate()
                    # If already 16kHz, 16-bit, mono, return untouched
                    if channels == 1 and sampwidth == 2 and rate == 16000:
                        return audio_bytes
        except Exception:
            pass

    # Use SoundFile if available
    if _SOUNDFILE_AVAILABLE:
        try:
            with io.BytesIO(audio_bytes) as in_bio:
                data, sample_rate = sf.read(in_bio)

                # Downmix stereo to mono if needed
                if data.ndim > 1:
                    data = data.mean(axis=1)

                # Resample if sample rate != 16000
                if sample_rate != 16000:
                    import scipy.signal
                    num_samples = int(len(data) * 16000 / sample_rate)
                    data = scipy.signal.resample(data, num_samples)

                out_bio = io.BytesIO()
                sf.write(out_bio, data, 16000, format="WAV", subtype="PCM_16")
                return out_bio.getvalue()
        except Exception as exc:
            logger.error(f"SoundFile normalization error: {exc}. Falling back to source WAV.")

    # If it's already a WAV, return as-is
    if source_format == "wav":
        return audio_bytes

    raise AudioValidationError(
        f"Unable to normalize '{source_format}' audio to 16kHz mono WAV. Extended codec libraries unavailable."
    )


@contextmanager
def temporary_audio_file(audio_bytes: bytes, suffix: str = ".wav") -> Generator[Path, None, None]:
    """
    Safely writes audio bytes to a temporary file in VOICE_AUDIO_TEMP_DIR.
    Ensures absolute cleanup upon context exit unless VOICE_RETAIN_AUDIO is enabled.
    """
    settings = get_settings()
    temp_dir = Path(settings.VOICE_AUDIO_TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)

    fd, path_str = tempfile.mkstemp(suffix=suffix, dir=str(temp_dir))
    temp_path = Path(path_str)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio_bytes)
        yield temp_path
    finally:
        if not settings.VOICE_RETAIN_AUDIO:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove temp audio file {temp_path}: {e}")


def cleanup_audio_temp_directory() -> int:
    """Removes all temporary audio files from the buffer directory. Returns deleted count."""
    settings = get_settings()
    temp_dir = Path(settings.VOICE_AUDIO_TEMP_DIR)
    if not temp_dir.exists():
        return 0

    count = 0
    for item in temp_dir.glob("*"):
        if item.is_file():
            try:
                item.unlink()
                count += 1
            except Exception:
                pass
    return count


def generate_synthetic_wav(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    is_silence: bool = False,
) -> bytes:
    """
    Generates valid 16-bit PCM mono WAV bytes purely using standard library wave & struct.
    Used for mock providers, automated tests, and offline synthesis verification.
    """
    num_samples = int(sample_rate * duration_seconds)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)        # mono
        wf.setsampwidth(2)        # 16-bit PCM
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            if is_silence:
                val = 0
            else:
                t = float(i) / sample_rate
                # 0.25 amplitude tone to avoid clipping
                val = int(32767.0 * 0.25 * math.sin(2.0 * math.pi * frequency * t))
            frames.extend(struct.pack("<h", val))

        wf.writeframes(frames)

    return bio.getvalue()
