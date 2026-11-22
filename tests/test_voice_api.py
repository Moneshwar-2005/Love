"""
Integration and API Tests for Voice Engine Endpoints (Phase 06).
Covers REST APIs under /api/v1/voice, authentication, multi-tenant isolation,
transcription, speech synthesis, wake-word controls, and HITL approval preservation.
"""

import io
import uuid
from unittest.mock import patch
import pytest

from backend.app.config.settings import get_settings
from backend.app.voice.audio import generate_synthetic_wav
from backend.app.voice.stt import get_stt_provider
from backend.app.voice.tts import get_tts_provider
from backend.app.voice.wake_word import get_wake_word_detector


@pytest.fixture
async def registered_user_and_token(async_client):
    """Registers a fresh user and returns the auth headers."""
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"voice_user_{uid}@example.com",
        "username": f"voice_user_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Voice Subsystem Tester",
        "device_identifier": f"voice-device-{uid}",
        "device_name": "Voice Test Terminal",
        "device_type": "windows",
    }
    with patch("backend.app.authentication.service.settings.ALLOW_OPEN_REGISTRATION", True):
        reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code in (201, 200)

    login_payload = {
        "email_or_username": reg_payload["username"],
        "password": reg_payload["password"],
        "device_identifier": reg_payload["device_identifier"],
        "device_name": reg_payload["device_name"],
        "device_type": reg_payload["device_type"],
    }
    login_res = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, reg_payload["username"]


@pytest.fixture
async def second_user_and_token(async_client):
    """Registers a second user for owner isolation verification."""
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"second_voice_{uid}@example.com",
        "username": f"second_voice_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Second Voice Tester",
        "device_identifier": f"second-voice-{uid}",
        "device_name": "Second Device",
        "device_type": "windows",
    }
    with patch("backend.app.authentication.service.settings.ALLOW_OPEN_REGISTRATION", True):
        reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
        assert reg_res.status_code in (201, 200)

    login_payload = {
        "email_or_username": reg_payload["username"],
        "password": reg_payload["password"],
        "device_identifier": reg_payload["device_identifier"],
        "device_name": reg_payload["device_name"],
        "device_type": reg_payload["device_type"],
    }
    login_res = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Status & Discovery Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_get_voice_status(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    res = await async_client.get("/api/v1/voice/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_enabled"] is True
    assert "hardware" in data
    assert "stt" in data
    assert "tts" in data
    assert "wake_word" in data
    assert "personality" in data
    assert data["personality"]["accent"] == "Indian English"


@pytest.mark.asyncio
async def test_get_stt_and_tts_providers(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # STT providers
    stt_res = await async_client.get("/api/v1/voice/stt/providers", headers=headers)
    assert stt_res.status_code == 200
    stt_list = stt_res.json()
    assert any(p["provider_id"] == "faster_whisper" for p in stt_list)

    # TTS providers
    tts_res = await async_client.get("/api/v1/voice/tts/providers", headers=headers)
    assert tts_res.status_code == 200
    tts_list = tts_res.json()
    assert any(p["provider_id"] == "azure" for p in tts_list)
    assert any(p["provider_id"] == "mock" for p in tts_list)


@pytest.mark.asyncio
async def test_get_tts_voices_catalog(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    res = await async_client.get("/api/v1/voice/tts/voices?provider=azure", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "azure" in data
    assert any("Neerja" in v["name"] for v in data["azure"])


# ==============================================================================
# 2. Session Management & Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_voice_session_lifecycle_api(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # Create session
    create_res = await async_client.post(
        "/api/v1/voice/sessions",
        headers=headers,
        json={"enable_wake_word": False},
    )
    assert create_res.status_code == 201
    session_data = create_res.json()
    sid = session_data["session_id"]
    assert session_data["state"] == "idle"

    # Fetch session
    get_res = await async_client.get(f"/api/v1/voice/sessions/{sid}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == sid

    # Cancel session
    cancel_res = await async_client.post(f"/api/v1/voice/sessions/{sid}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "cancelled"


@pytest.mark.asyncio
async def test_voice_session_owner_isolation(async_client, registered_user_and_token, second_user_and_token):
    headers1, _ = registered_user_and_token
    headers2 = second_user_and_token

    # User 1 creates session
    create_res = await async_client.post("/api/v1/voice/sessions", headers=headers1, json={})
    sid = create_res.json()["session_id"]

    # User 2 attempts to inspect User 1's session -> must return 404
    cross_res = await async_client.get(f"/api/v1/voice/sessions/{sid}", headers=headers2)
    assert cross_res.status_code == 404

    # User 2 attempts to cancel User 1's session -> must return 404
    cross_cancel = await async_client.post(f"/api/v1/voice/sessions/{sid}/cancel", headers=headers2)
    assert cross_cancel.status_code == 404


# ==============================================================================
# 3. Transcription & Synthesis Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_transcribe_audio_endpoint(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    wav_bytes = generate_synthetic_wav(duration_seconds=1.0)

    files = {"file": ("test_speech.wav", io.BytesIO(wav_bytes), "audio/wav")}
    data = {"provider_id": "mock", "language": "en"}

    res = await async_client.post("/api/v1/voice/transcribe", headers=headers, files=files, data=data)
    assert res.status_code == 200
    result = res.json()
    assert "text" in result
    assert result["provider"] == "mock"
    assert result["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_transcribe_audio_empty_rejection(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    files = {"file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    res = await async_client.post("/api/v1/voice/transcribe", headers=headers, files=files)
    assert res.status_code == 400
    assert "cannot be empty" in res.json()["detail"]


@pytest.mark.asyncio
async def test_synthesize_speech_endpoint_json(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    payload = {
        "text": "Hello, I am LOVE, your personal assistant.",
        "provider_id": "mock",
        "return_binary": False,
    }
    res = await async_client.post("/api/v1/voice/synthesize", headers=headers, json=payload)
    assert res.status_code == 200
    result = res.json()
    assert result["provider"] == "mock"
    assert result["audio_base64"] is not None
    assert result["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_synthesize_speech_endpoint_binary(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    payload = {
        "text": "Hello, I am LOVE, your personal assistant.",
        "provider_id": "mock",
        "return_binary": True,
    }
    res = await async_client.post("/api/v1/voice/synthesize", headers=headers, json=payload)
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    assert len(res.content) > 44


# ==============================================================================
# 4. Full End-to-End Voice Chat Turn
# ==============================================================================

@pytest.mark.asyncio
async def test_voice_chat_turn_endpoint(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    wav_bytes = generate_synthetic_wav(duration_seconds=1.0)

    files = {"file": ("utterance.wav", io.BytesIO(wav_bytes), "audio/wav")}
    data = {
        "stt_provider_id": "mock",
        "tts_provider_id": "mock",
    }

    res = await async_client.post("/api/v1/voice/chat", headers=headers, files=files, data=data)
    assert res.status_code == 200
    turn = res.json()
    assert "conversation_id" in turn
    assert "user_text" in turn
    assert "assistant_text" in turn
    assert turn["synthesis"] is not None
    assert turn["synthesis"]["audio_base64"] is not None
    assert turn["latency_ms"] > 0


# ==============================================================================
# 5. HITL Approval Invariant Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_voice_chat_preserves_work_approval_invariant(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    # Set mock STT text to trigger medium risk file creation
    mock_stt = get_stt_provider("mock")
    mock_stt.set_text("create file secret_voice_plan.txt in workspace")

    wav_bytes = generate_synthetic_wav(duration_seconds=1.0)
    files = {"file": ("action_prompt.wav", io.BytesIO(wav_bytes), "audio/wav")}
    data = {
        "stt_provider_id": "mock",
        "tts_provider_id": "mock",
    }

    res = await async_client.post("/api/v1/voice/chat", headers=headers, files=files, data=data)
    assert res.status_code == 200
    turn = res.json()

    # Verify that approval is flagged as required
    assert turn["approval_required"] is True
    assert "requires your explicit approval" in turn["assistant_text"] or "confirmation or approval" in turn["assistant_text"]

    # Verify that the action was NOT auto-approved merely because spoken
    approvals_res = await async_client.get("/api/v1/work/approvals", headers=headers)
    assert approvals_res.status_code == 200
    pending_approvals = approvals_res.json()
    assert len(pending_approvals) > 0
    assert any("secret_voice_plan.txt" in a["task_title"] or a["action"]["tool_name"] == "workspace_create_file" for a in pending_approvals)


# ==============================================================================
# 6. Wake-Word Controls & Privacy
# ==============================================================================

@pytest.mark.asyncio
async def test_wake_word_status_endpoint(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    res = await async_client.get("/api/v1/voice/wake-word/status", headers=headers)
    assert res.status_code == 200
    status = res.json()
    assert status["target_phrase"] == "Hey LOVE"
    assert status["is_active"] is False


@pytest.mark.asyncio
async def test_wake_word_toggle_refuses_without_custom_model(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    # Attempting to activate openWakeWord when custom hey_love.onnx is absent -> 404
    payload = {"active": True, "mic_permission_granted": True}
    res = await async_client.post("/api/v1/voice/wake-word/toggle", headers=headers, json=payload)
    assert res.status_code == 404
    assert "hey_love.onnx" in res.json()["detail"]


@pytest.mark.asyncio
async def test_local_only_mode_blocks_cloud_tts(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token
    payload = {
        "text": "Private cloud synthesis attempt.",
        "provider_id": "azure",
    }
    settings = get_settings()
    orig = settings.LOCAL_ONLY_MODE
    try:
        settings.LOCAL_ONLY_MODE = True
        res = await async_client.post("/api/v1/voice/synthesize", headers=headers, json=payload)
        assert res.status_code == 403
        assert "LOCAL_ONLY_MODE" in res.json()["detail"]
    finally:
        settings.LOCAL_ONLY_MODE = orig


@pytest.mark.asyncio
async def test_unauthenticated_voice_access_blocked(async_client):
    res = await async_client.get("/api/v1/voice/status")
    assert res.status_code == 401
