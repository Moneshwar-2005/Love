"""
Unit Tests for Voice Engine, Speech Processing, Personality, STT, TTS, and Wake-Word (Phase 06).
"""

import io
import wave
import pytest

from backend.app.config.settings import get_settings
from backend.app.voice.audio import (
    convert_to_wav_16k_mono,
    detect_audio_format,
    generate_synthetic_wav,
    temporary_audio_file,
    validate_audio_payload,
)
from backend.app.voice.exceptions import (
    AudioValidationError,
    STTProviderNotConfiguredError,
    TTSProviderNotConfiguredError,
    VoicePrivacyRestrictionError,
    VoiceSessionError,
    WakeWordError,
    WakeWordModelNotFoundError,
)
from backend.app.voice.personality import (
    LOVE_CLASSIC_PROFILE,
    build_ssml,
    get_active_voice_profile,
    list_available_profiles,
)
from backend.app.voice.schemas import VoiceSessionState
from backend.app.voice.session import VoiceSession, VoiceSessionManager
from backend.app.voice.stt.faster_whisper import FasterWhisperSTTProvider
from backend.app.voice.stt.mock_stt import MockSTTProvider
from backend.app.voice.tts import get_tts_provider, list_tts_providers
from backend.app.voice.tts.azure_speech import AzureSpeechTTSProvider
from backend.app.voice.tts.elevenlabs import ElevenLabsTTSProvider
from backend.app.voice.tts.mock_tts import MockTTSProvider
from backend.app.voice.tts.piper import PiperTTSProvider
from backend.app.voice.wake_word.mock_wake_word import MockWakeWordDetector
from backend.app.voice.wake_word.openwakeword import OpenWakeWordDetector


# ==============================================================================
# 1. Audio Processing & Validation Tests
# ==============================================================================

class TestAudioProcessing:
    def test_synthetic_wav_generation_and_detection(self):
        wav_bytes = generate_synthetic_wav(duration_seconds=1.5, sample_rate=16000)
        assert len(wav_bytes) > 44
        fmt = detect_audio_format(wav_bytes)
        assert fmt == "wav"

        detected_fmt, duration = validate_audio_payload(wav_bytes)
        assert detected_fmt == "wav"
        assert abs(duration - 1.5) < 0.05

    def test_empty_audio_rejection(self):
        with pytest.raises(AudioValidationError) as exc:
            validate_audio_payload(b"")
        assert "cannot be empty" in str(exc.value)

    def test_audio_size_limit_rejection(self):
        # 100 bytes payload tested against 50 byte ceiling
        with pytest.raises(AudioValidationError) as exc:
            validate_audio_payload(b"RIFF" + b"\x00" * 96, max_size_bytes=50)
        assert "exceeds maximum permitted limit" in str(exc.value)

    def test_audio_duration_limit_rejection(self):
        wav_bytes = generate_synthetic_wav(duration_seconds=5.0, sample_rate=16000)
        with pytest.raises(AudioValidationError) as exc:
            validate_audio_payload(wav_bytes, max_duration_seconds=2)
        assert "exceeds maximum allowable limit" in str(exc.value)

    def test_corrupt_wav_header_rejection(self):
        corrupt_wav = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"broken data"
        with pytest.raises(AudioValidationError):
            validate_audio_payload(corrupt_wav)

    def test_audio_normalization_16k_mono(self):
        wav_bytes = generate_synthetic_wav(duration_seconds=1.0, sample_rate=16000)
        normalized = convert_to_wav_16k_mono(wav_bytes, "wav")
        assert len(normalized) > 0
        with io.BytesIO(normalized) as bio:
            with wave.open(bio, "rb") as wf:
                assert wf.getnchannels() == 1
                assert wf.getframerate() == 16000
                assert wf.getsampwidth() == 2

    def test_temporary_audio_file_cleanup(self):
        wav_bytes = generate_synthetic_wav(duration_seconds=0.5)
        created_path = None
        with temporary_audio_file(wav_bytes, suffix=".wav") as temp_p:
            created_path = temp_p
            assert temp_p.exists()
            assert temp_p.stat().st_size == len(wav_bytes)
        # Should be automatically deleted after exiting with-block
        assert not created_path.exists()


# ==============================================================================
# 2. Voice Personality & SSML Tests
# ==============================================================================

class TestVoicePersonality:
    def test_love_classic_personality_profile(self):
        profile = get_active_voice_profile("love_classic")
        assert profile.gender == "female"
        assert profile.accent == "Indian English"
        assert profile.language_code == "en-IN"
        assert "Neerja" in profile.provider_voice_map["azure"]
        assert profile.speaking_rate == 1.0

    def test_list_available_profiles(self):
        profiles = list_available_profiles()
        assert len(profiles) >= 2
        ids = [p.id for p in profiles]
        assert "love_classic" in ids
        assert "love_expressive" in ids

    def test_ssml_construction_and_pacing(self):
        text = "Hello! I am LOVE, your personal assistant. How can I help you today?"
        ssml = build_ssml(text, LOVE_CLASSIC_PROFILE, provider="azure")
        assert '<speak version="1.0"' in ssml
        assert '<voice name="en-IN-NeerjaNeural">' in ssml
        assert '<prosody rate="+0%" pitch="+0%">' in ssml
        assert '<break time="220ms"/>' in ssml  # natural punctuation pause
        assert "</speak>" in ssml


# ==============================================================================
# 3. Speech-To-Text (STT) Provider Tests
# ==============================================================================

class TestSTTProviders:
    @pytest.mark.asyncio
    async def test_mock_stt_transcription(self):
        provider = MockSTTProvider(predefined_text="Calculate eighteen percent of forty five thousand")
        wav_bytes = generate_synthetic_wav(duration_seconds=1.2)
        result = await provider.transcribe(wav_bytes)

        assert result.text == "Calculate eighteen percent of forty five thousand"
        assert result.duration_seconds > 0.0
        assert len(result.segments) > 0
        assert result.provider == "mock"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_faster_whisper_hardware_resolution(self):
        provider = FasterWhisperSTTProvider(model_size="base", device="auto", compute_type="int8")
        dev, comp = provider._resolve_hardware()
        assert dev in ("cuda", "cpu")
        assert comp == "int8"

    @pytest.mark.asyncio
    async def test_faster_whisper_reports_availability_accurately(self):
        provider = FasterWhisperSTTProvider(model_size="non_existent_model_999")
        # Accurately reports False without attempting automatic downloads
        available = await provider.is_available()
        assert available is False

        wav_bytes = generate_synthetic_wav(duration_seconds=1.0)
        with pytest.raises(STTProviderNotConfiguredError) as exc:
            await provider.transcribe(wav_bytes)
        assert "not downloaded locally" in str(exc.value)


# ==============================================================================
# 4. Text-To-Speech (TTS) Provider Tests
# ==============================================================================

class TestTTSProviders:
    @pytest.mark.asyncio
    async def test_mock_tts_synthesis(self):
        provider = MockTTSProvider(sample_rate=16000)
        result = await provider.synthesize("Welcome to LOVE assistant.")

        assert result.audio_bytes is not None
        assert len(result.audio_bytes) > 44
        assert result.format == "audio/wav"
        assert result.duration_seconds > 0.0
        assert result.provider == "mock"
        assert result.character_count == len("Welcome to LOVE assistant.")

    @pytest.mark.asyncio
    async def test_mock_tts_streaming(self):
        provider = MockTTSProvider()
        chunks = []
        async for chunk in provider.synthesize_stream("Streaming audio response test."):
            chunks.append(chunk)

        assert len(chunks) > 0
        total_bytes = b"".join(chunks)
        assert len(total_bytes) > 44
        assert detect_audio_format(total_bytes) == "wav"

    @pytest.mark.asyncio
    async def test_azure_tts_unconfigured_error(self):
        provider = AzureSpeechTTSProvider(api_key="", region="")
        assert provider.is_configured() is False
        with pytest.raises(TTSProviderNotConfiguredError):
            await provider.synthesize("Test speech.")

    @pytest.mark.asyncio
    async def test_elevenlabs_unconfigured_error(self):
        provider = ElevenLabsTTSProvider(api_key="", voice_id="")
        assert provider.is_configured() is False
        with pytest.raises(TTSProviderNotConfiguredError):
            await provider.synthesize("Test speech.")

    @pytest.mark.asyncio
    async def test_piper_unconfigured_error(self):
        provider = PiperTTSProvider(binary_path="/nonexistent/piper", model_path="/nonexistent/model.onnx")
        assert provider.is_configured() is False
        with pytest.raises(TTSProviderNotConfiguredError):
            await provider.synthesize("Test speech.")

    @pytest.mark.asyncio
    async def test_tts_auto_selection_with_local_fallback(self):
        # Auto-selection resolves to mock local fallback when cloud keys are empty
        provider = await get_tts_provider("auto")
        assert provider is not None
        assert provider.is_local is True

    @pytest.mark.asyncio
    async def test_tts_list_providers(self):
        providers = await list_tts_providers()
        ids = [p["provider_id"] for p in providers]
        assert "azure" in ids
        assert "elevenlabs" in ids
        assert "piper" in ids
        assert "mock" in ids


# ==============================================================================
# 5. Wake-Word Detection Tests
# ==============================================================================

class TestWakeWordDetection:
    def test_openwakeword_identifies_missing_custom_hey_love_model(self):
        detector = OpenWakeWordDetector()
        status = detector.get_status()

        assert status.target_phrase == "Hey LOVE"
        # Confirms default openWakeWord models do not have 'Hey LOVE'
        assert status.model_available is False
        assert "hey_love.onnx" in status.message
        assert "Default openWakeWord models" in status.message

    def test_openwakeword_refuses_activation_without_model(self):
        detector = OpenWakeWordDetector()
        with pytest.raises(WakeWordModelNotFoundError) as exc:
            detector.set_active(True, mic_permission=True)
        assert "hey_love.onnx" in str(exc.value)

    def test_mock_wake_word_toggle_and_permission(self):
        detector = MockWakeWordDetector()
        assert detector.is_model_available() is True

        # Activation requires mic permission
        with pytest.raises(WakeWordError):
            detector.set_active(True, mic_permission=False)

        # Grant mic permission and activate
        status = detector.set_active(True, mic_permission=True)
        assert status.is_active is True
        assert status.mic_permission_granted is True

        # Immediate deactivation
        status = detector.set_active(False)
        assert status.is_active is False

    def test_mock_wake_word_audio_detection(self):
        detector = MockWakeWordDetector()
        detector.set_force_detected(True)
        detected, score = detector.detect_in_audio(b"dummy")
        assert detected is True
        assert score >= 0.5


# ==============================================================================
# 6. Voice Session Management Tests
# ==============================================================================

class TestVoiceSessionManagement:
    @pytest.mark.asyncio
    async def test_session_lifecycle_and_transitions(self):
        mgr = VoiceSessionManager()
        session = await mgr.create_session(user_id="user_123")
        assert session.state == VoiceSessionState.IDLE

        session.transition_to(VoiceSessionState.RECORDING)
        assert session.state == VoiceSessionState.RECORDING

        session.transition_to(VoiceSessionState.TRANSCRIBING)
        assert session.state == VoiceSessionState.TRANSCRIBING

        session.transition_to(VoiceSessionState.THINKING)
        assert session.state == VoiceSessionState.THINKING

        session.transition_to(VoiceSessionState.SPEAKING)
        assert session.state == VoiceSessionState.SPEAKING

        session.transition_to(VoiceSessionState.IDLE)
        assert session.state == VoiceSessionState.IDLE

    @pytest.mark.asyncio
    async def test_illegal_session_transition_raises_error(self):
        mgr = VoiceSessionManager()
        session = await mgr.create_session(user_id="user_abc")
        # RECORDING cannot transition directly to SPEAKING
        session.transition_to(VoiceSessionState.RECORDING)
        with pytest.raises(VoiceSessionError) as exc:
            session.transition_to(VoiceSessionState.SPEAKING)
        assert "Illegal voice session transition" in str(exc.value)

    @pytest.mark.asyncio
    async def test_concurrent_session_rejection_per_user(self):
        mgr = VoiceSessionManager()
        session1 = await mgr.create_session(user_id="user_concurrent")
        session1.transition_to(VoiceSessionState.RECORDING)

        # Attempting second session while session 1 is RECORDING must be rejected with 409
        with pytest.raises(VoiceSessionError) as exc:
            await mgr.create_session(user_id="user_concurrent")
        assert exc.value.status_code == 409
        assert "is currently in state 'recording'" in str(exc.value)

    @pytest.mark.asyncio
    async def test_session_cancellation(self):
        mgr = VoiceSessionManager()
        session = await mgr.create_session(user_id="user_cancel")
        session.transition_to(VoiceSessionState.RECORDING)

        cancelled = await mgr.cancel_session(session.session_id, user_id="user_cancel")
        assert cancelled.state == VoiceSessionState.CANCELLED

        # User is now free to create a new session
        new_session = await mgr.create_session(user_id="user_cancel")
        assert new_session.session_id != session.session_id
