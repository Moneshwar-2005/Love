"""
Integration tests for Universal Intelligence Layer API endpoints (Phase 03).
"""

import json
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from backend.app.database.models.conversation import Message
from backend.app.database.session import AsyncSessionLocal
from backend.app.intelligence.schemas import AssistantResponse, Role, StreamChunk, TokenUsage
from backend.app.main import app


@pytest.fixture
async def registered_user_and_token(async_client):
    """Registers a fresh user and returns the auth headers."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"intelligence_user_{uid}@example.com",
        "username": f"intel_user_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Intelligence Tester",
        "device_identifier": f"intel-device-{uid}",
        "device_name": "Test Laptop",
        "device_type": "windows",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code in (201, 200)

    # Login to acquire token
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


@pytest.mark.asyncio
async def test_intelligence_endpoints_require_authentication(async_client):
    """Verifies that all intelligence endpoints reject requests lacking valid credentials."""
    unauthed_endpoints = [
        ("GET", "/api/v1/intelligence/status"),
        ("GET", "/api/v1/intelligence/providers"),
        ("GET", "/api/v1/intelligence/models"),
        ("GET", "/api/v1/intelligence/conversations"),
        ("POST", "/api/v1/intelligence/conversations"),
        ("POST", "/api/v1/intelligence/chat"),
        ("POST", "/api/v1/intelligence/chat/stream"),
    ]
    for method, path in unauthed_endpoints:
        if method == "GET":
            res = await async_client.get(path)
        else:
            res = await async_client.post(path, json={})
        assert res.status_code == 401, f"Expected 401 on unauthenticated {method} {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_intelligence_status_and_providers_endpoints(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # 1. Status endpoint
    status_res = await async_client.get("/api/v1/intelligence/status", headers=headers)
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["status"] == "operational"
    assert "hardware_profile" in data
    assert "GTX 1650" in data["hardware_profile"]["gpu"]
    assert len(data["providers"]) >= 4

    # 2. Providers endpoint
    prov_res = await async_client.get("/api/v1/intelligence/providers", headers=headers)
    assert prov_res.status_code == 200
    providers = prov_res.json()
    provider_ids = [p["provider_id"] for p in providers]
    assert "ollama" in provider_ids
    assert "openai" in provider_ids
    assert "anthropic" in provider_ids
    assert "gemini" in provider_ids

    # 3. Models endpoint
    models_res = await async_client.get("/api/v1/intelligence/models", headers=headers)
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) >= 5


@pytest.mark.asyncio
async def test_conversation_lifecycle_crud(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # 1. Create Conversation
    create_res = await async_client.post(
        "/api/v1/intelligence/conversations",
        json={"title": "Test AI Exploration"},
        headers=headers
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "Test AI Exploration"

    # 2. List Conversations
    list_res = await async_client.get("/api/v1/intelligence/conversations", headers=headers)
    assert list_res.status_code == 200
    conv_list = list_res.json()
    assert any(c["id"] == conv_id for c in conv_list)

    # 3. Get Conversation Detail
    detail_res = await async_client.get(f"/api/v1/intelligence/conversations/{conv_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == conv_id
    assert "messages" in detail

    # 4. Delete Conversation
    del_res = await async_client.delete(f"/api/v1/intelligence/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 200

    # 5. Verify Deletion
    check_res = await async_client.get(f"/api/v1/intelligence/conversations/{conv_id}", headers=headers)
    assert check_res.status_code == 404


@pytest.mark.asyncio
async def test_conversation_ownership_boundary_isolation(async_client, registered_user_and_token):
    """Verifies User B cannot access, read, or delete User A's conversations."""
    headers_a, _ = registered_user_and_token

    # User A creates a conversation
    create_res = await async_client.post(
        "/api/v1/intelligence/conversations",
        json={"title": "User A Private Thread"},
        headers=headers_a
    )
    assert create_res.status_code == 201
    conv_a_id = create_res.json()["id"]

    # Register User B
    import uuid
    uid_b = uuid.uuid4().hex[:8]
    reg_b = {
        "email": f"user_b_{uid_b}@example.com",
        "username": f"user_b_{uid_b}",
        "password": "SecurePassword123!",
        "full_name": "User B",
        "device_identifier": f"dev-b-{uid_b}",
        "device_name": "Device B",
        "device_type": "linux",
    }
    await async_client.post("/api/v1/auth/register", json=reg_b, headers=headers_a)

    login_b = await async_client.post("/api/v1/auth/login", json={
        "email_or_username": reg_b["username"],
        "password": reg_b["password"],
        "device_identifier": reg_b["device_identifier"],
        "device_name": reg_b["device_name"],
        "device_type": reg_b["device_type"],
    })
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # User B attempts to read User A's conversation
    get_res = await async_client.get(f"/api/v1/intelligence/conversations/{conv_a_id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B attempts to delete User A's conversation
    del_res = await async_client.delete(f"/api/v1/intelligence/conversations/{conv_a_id}", headers=headers_b)
    assert del_res.status_code == 404


@pytest.mark.asyncio
async def test_chat_synchronous_execution_and_persistence(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    mock_assistant_response = AssistantResponse(
        content="Certainly! To handle SQLite in async Python, use the aiosqlite library.",
        role=Role.ASSISTANT,
        provider="ollama",
        model="llama3.2:3b",
        finish_reason="stop",
        usage=TokenUsage(prompt_tokens=25, completion_tokens=30, total_tokens=55),
        latency_ms=145.2,
    )

    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", AsyncMock(return_value=True)):
        with patch("backend.app.intelligence.providers.ollama.OllamaProvider.list_models", AsyncMock(return_value=["llama3.2:3b"])):
            with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate", AsyncMock(return_value=mock_assistant_response)):
                chat_payload = {
                    "message": "How do I use aiosqlite in Python?",
                    "local_only": True,
                }
                res = await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers)
                assert res.status_code == 200
                data = res.json()

                assert data["conversation_id"] is not None
                assert data["assistant_message"] == mock_assistant_response.content
                assert data["intent"] in ["coding", "general"]
                assert data["provider"] == "ollama"
                assert data["model"] == "llama3.2:3b"

                # Verify conversation message history in database
                conv_res = await async_client.get(
                    f"/api/v1/intelligence/conversations/{data['conversation_id']}",
                    headers=headers
                )
                assert conv_res.status_code == 200
                conv_data = conv_res.json()
                messages = conv_data["messages"]
                assert len(messages) == 2
                assert messages[0]["role"] == "user"
                assert messages[0]["content"] == chat_payload["message"]
                assert messages[1]["role"] == "assistant"
                assert messages[1]["content"] == mock_assistant_response.content
                assert messages[1]["status"] == "completed"


@pytest.mark.asyncio
async def test_chat_streaming_sse_execution_and_persistence(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    async def mock_stream_chunks(*args, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        tokens = ["Hello", " ", "world!", " LOVE", " is", " online."]
        accumulated = ""
        for i, token in enumerate(tokens):
            accumulated += token
            is_done = (i == len(tokens) - 1)
            yield StreamChunk(
                delta=token,
                accumulated=accumulated,
                role=Role.ASSISTANT,
                is_done=is_done,
                finish_reason="stop" if is_done else None,
                provider="ollama",
                model="llama3.2:3b",
                latency_ms=10.0 * (i + 1),
            )

    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", AsyncMock(return_value=True)):
        with patch("backend.app.intelligence.providers.ollama.OllamaProvider.list_models", AsyncMock(return_value=["llama3.2:3b"])):
            with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate_stream", side_effect=mock_stream_chunks):
                chat_payload = {
                    "message": "Say hello world.",
                    "local_only": True,
                }
                res = await async_client.post("/api/v1/intelligence/chat/stream", json=chat_payload, headers=headers)
                assert res.status_code == 200
                assert "text/event-stream" in res.headers["content-type"]

                body = res.text
                lines = [line.strip() for line in body.split("\n") if line.strip().startswith("data:")]
                assert len(lines) >= 6

                last_event = json.loads(lines[-1][5:].strip())
                assert last_event["is_done"] is True
                assert last_event["status"] == "completed"
                conv_id = last_event["conversation_id"]

                # Verify persistent database message record
                conv_res = await async_client.get(
                    f"/api/v1/intelligence/conversations/{conv_id}",
                    headers=headers
                )
                assert conv_res.status_code == 200
                conv_data = conv_res.json()
                assistant_msg = [m for m in conv_data["messages"] if m["role"] == "assistant"][0]
                assert assistant_msg["content"] == "Hello world! LOVE is online."
                assert assistant_msg["status"] == "completed"
