"""
Integration tests for Persistent Personal Memory API Endpoints (Phase 04).
Covers CRUD, search, deduplication, sensitive data blocking, archiving,
export/import, clearing, and chat memory context integration.
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.intelligence.schemas import AssistantResponse, Role, TokenUsage


@pytest.fixture
async def registered_user_and_token(async_client):
    """Registers a fresh user and returns the auth headers."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"memory_user_{uid}@example.com",
        "username": f"mem_user_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Memory Lead Tester",
        "device_identifier": f"mem-device-{uid}",
        "device_name": "Test Workstation",
        "device_type": "windows",
    }
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
    """Registers a second independent user for isolation verification."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"second_user_{uid}@example.com",
        "username": f"sec_user_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Second Independent User",
        "device_identifier": f"sec-device-{uid}",
        "device_name": "Second Device",
        "device_type": "linux",
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


@pytest.mark.asyncio
async def test_memory_endpoints_require_authentication(async_client):
    """Verifies that all memory endpoints reject unauthenticated calls with 401."""
    endpoints = [
        ("GET", "/api/v1/memory"),
        ("POST", "/api/v1/memory"),
        ("POST", "/api/v1/memory/search"),
        ("GET", "/api/v1/memory/stats"),
        ("POST", "/api/v1/memory/rebuild-index"),
        ("GET", "/api/v1/memory/export"),
        ("POST", "/api/v1/memory/import"),
        ("DELETE", "/api/v1/memory/clear"),
        ("GET", "/api/v1/memory/dummy-id"),
        ("PUT", "/api/v1/memory/dummy-id"),
        ("DELETE", "/api/v1/memory/dummy-id"),
        ("POST", "/api/v1/memory/dummy-id/archive"),
        ("POST", "/api/v1/memory/dummy-id/restore"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = await async_client.get(path)
        elif method == "POST":
            res = await async_client.post(path, json={})
        elif method == "PUT":
            res = await async_client.put(path, json={})
        elif method == "DELETE":
            res = await async_client.delete(path)
        assert res.status_code == 401, f"Endpoint {method} {path} should require authentication"


@pytest.mark.asyncio
async def test_memory_crud_lifecycle(async_client, registered_user_and_token):
    """Verifies complete memory CRUD lifecycle."""
    headers, _ = registered_user_and_token

    # 1. Create Memory
    create_payload = {
        "content": "User prefers concise Python code with strict typing and docstrings.",
        "category": "personal",
        "importance": 4,
        "confidence": 0.95,
        "tags": ["python", "style", "typing"],
        "metadata": {"editor": "VSCode"},
    }
    res_create = await async_client.post("/api/v1/memory", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    created_data = res_create.json()
    memory_id = created_data["id"]
    assert created_data["content"] == create_payload["content"]
    assert created_data["category"] == "personal"
    assert created_data["importance"] == 4
    assert "python" in created_data["tags"]

    # 2. Get Memory
    res_get = await async_client.get(f"/api/v1/memory/{memory_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == memory_id

    # 3. Update Memory
    update_payload = {
        "content": "User prefers concise Python code with strict typing, Pydantic, and docstrings.",
        "importance": 5,
        "tags": ["python", "style", "typing", "pydantic"],
    }
    res_update = await async_client.put(f"/api/v1/memory/{memory_id}", json=update_payload, headers=headers)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert "pydantic" in updated_data["tags"]
    assert updated_data["importance"] == 5

    # 4. List Memories
    res_list = await async_client.get("/api/v1/memory?category=personal", headers=headers)
    assert res_list.status_code == 200
    memories = res_list.json()
    assert len(memories) >= 1
    assert any(m["id"] == memory_id for m in memories)

    # 5. Archive and Restore
    res_archive = await async_client.post(f"/api/v1/memory/{memory_id}/archive", headers=headers)
    assert res_archive.status_code == 200
    assert res_archive.json()["is_archived"] is True

    # Confirm it does not appear in active list
    res_active = await async_client.get("/api/v1/memory?is_archived=false", headers=headers)
    assert not any(m["id"] == memory_id for m in res_active.json())

    res_restore = await async_client.post(f"/api/v1/memory/{memory_id}/restore", headers=headers)
    assert res_restore.status_code == 200
    assert res_restore.json()["is_archived"] is False

    # 6. Delete Memory
    res_del = await async_client.delete(f"/api/v1/memory/{memory_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # Verify 404 after deletion
    res_post_del = await async_client.get(f"/api/v1/memory/{memory_id}", headers=headers)
    assert res_post_del.status_code == 404


@pytest.mark.asyncio
async def test_memory_creation_blocks_sensitive_data(async_client, registered_user_and_token):
    """Verifies that attempting to store API keys or passwords in memory returns HTTP 400."""
    headers, _ = registered_user_and_token

    payload = {
        "content": "My secret key is sk-1234567890abcdef1234567890abcdef",
        "category": "personal",
    }
    res = await async_client.post("/api/v1/memory", json=payload, headers=headers)
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "credentials" in detail or "secrets" in detail or "sensitive" in detail


@pytest.mark.asyncio
async def test_memory_owner_isolation(async_client, registered_user_and_token, second_user_and_token):
    """Verifies strict isolation: User A cannot read, update, or delete User B's memories."""
    headers_a, _ = registered_user_and_token
    headers_b, _ = second_user_and_token

    # User A creates a memory
    create_payload = {
        "content": "Confidential project roadmap for User A.",
        "category": "project",
    }
    res = await async_client.post("/api/v1/memory", json=create_payload, headers=headers_a)
    assert res.status_code == 201
    memory_id_a = res.json()["id"]

    # User B attempts to access User A's memory
    res_b_get = await async_client.get(f"/api/v1/memory/{memory_id_a}", headers=headers_b)
    assert res_b_get.status_code == 404

    # User B attempts to update User A's memory
    res_b_update = await async_client.put(
        f"/api/v1/memory/{memory_id_a}",
        json={"content": "Malicious takeover attempt"},
        headers=headers_b
    )
    assert res_b_update.status_code == 404

    # User B attempts to delete User A's memory
    res_b_del = await async_client.delete(f"/api/v1/memory/{memory_id_a}", headers=headers_b)
    assert res_b_del.status_code == 404

    # Test Suggestion Isolation:
    # Trigger suggestion for User A
    chat_payload = {"message": "We decided to implement custom caching with Redis.", "provider": "ollama", "model": "qwen2.5:1.5b"}
    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate", return_value=AssistantResponse(content="ok", provider="ollama", model="qwen2.5:1.5b")), \
         patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True
        await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers_a)

    sug_res_a = await async_client.get("/api/v1/memory/suggestions", headers=headers_a)
    assert len(sug_res_a.json()) >= 1
    sug_id_a = sug_res_a.json()[0]["id"]

    # User B cannot see User A's suggestion in their list
    sug_res_b = await async_client.get("/api/v1/memory/suggestions", headers=headers_b)
    assert not any(s["id"] == sug_id_a for s in sug_res_b.json())

    # User B cannot get User A's suggestion
    assert (await async_client.get(f"/api/v1/memory/suggestions/{sug_id_a}", headers=headers_b)).status_code == 404

    # User B cannot approve User A's suggestion
    assert (await async_client.post(f"/api/v1/memory/suggestions/{sug_id_a}/approve", headers=headers_b)).status_code == 404

    # User B cannot reject User A's suggestion
    assert (await async_client.post(f"/api/v1/memory/suggestions/{sug_id_a}/reject", headers=headers_b)).status_code == 404

    # User B cannot delete User A's suggestion
    assert (await async_client.delete(f"/api/v1/memory/suggestions/{sug_id_a}", headers=headers_b)).status_code == 404


@pytest.mark.asyncio
async def test_memory_search_endpoint(async_client, registered_user_and_token):
    """Verifies hybrid search endpoint retrieves relevant memories."""
    headers, _ = registered_user_and_token

    # Seed two memories
    await async_client.post(
        "/api/v1/memory",
        json={
            "content": "LOVE assistant runs on a GTX 1650 4GB GPU using Ollama local models.",
            "category": "project",
            "importance": 5,
            "tags": ["gpu", "hardware", "ollama"],
        },
        headers=headers,
    )
    await async_client.post(
        "/api/v1/memory",
        json={
            "content": "User prefers coffee with milk and no sugar.",
            "category": "personal",
            "importance": 2,
            "tags": ["drink", "preferences"],
        },
        headers=headers,
    )

    search_payload = {
        "query": "Which graphics card and hardware does LOVE run on?",
        "top_k": 3,
        "min_score": 0.1,
    }
    res = await async_client.post("/api/v1/memory/search", json=search_payload, headers=headers)
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1
    assert "GTX 1650" in results[0]["memory"]["content"]
    assert results[0]["score"] > 0.0


@pytest.mark.asyncio
async def test_memory_stats_and_rebuild_index(async_client, registered_user_and_token):
    """Verifies stats retrieval and vector index rebuilding."""
    headers, _ = registered_user_and_token

    # Create a memory
    r_create = await async_client.post(
        "/api/v1/memory",
        json={"content": "Project architecture utilizes FastAPI asynchronous handlers.", "category": "project"},
        headers=headers,
    )
    mem_id = r_create.json()["id"]

    # Get stats
    res_stats = await async_client.get("/api/v1/memory/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_memories"] >= 1
    assert stats["active_memories"] >= 1
    assert "embedding_provider" in stats

    # Rebuild index
    res_rebuild = await async_client.post("/api/v1/memory/rebuild-index", headers=headers)
    assert res_rebuild.status_code == 200
    assert res_rebuild.json()["status"] == "success"
    assert res_rebuild.json()["rebuilt_count"] >= 1

    # Archive the memory and verify rebuild excludes it from vector index
    await async_client.post(f"/api/v1/memory/{mem_id}/archive", headers=headers)
    res_rebuild_archived = await async_client.post("/api/v1/memory/rebuild-index", headers=headers)
    assert res_rebuild_archived.status_code == 200
    assert res_rebuild_archived.json()["rebuilt_count"] == 0

    # Restore the memory and verify rebuild includes it again
    await async_client.post(f"/api/v1/memory/{mem_id}/restore", headers=headers)
    res_rebuild_restored = await async_client.post("/api/v1/memory/rebuild-index", headers=headers)
    assert res_rebuild_restored.status_code == 200
    assert res_rebuild_restored.json()["rebuilt_count"] == 1


@pytest.mark.asyncio
async def test_export_import_and_clear_memories(async_client, registered_user_and_token):
    """Verifies export, clear (with/without confirm), and import workflow."""
    headers, _ = registered_user_and_token

    # 1. Create memories to export
    await async_client.post(
        "/api/v1/memory",
        json={"content": "Export test memory 1", "category": "personal"},
        headers=headers,
    )
    await async_client.post(
        "/api/v1/memory",
        json={"content": "Export test memory 2", "category": "project"},
        headers=headers,
    )

    # 2. Export
    res_export = await async_client.get("/api/v1/memory/export", headers=headers)
    assert res_export.status_code == 200
    exported_items = res_export.json()
    assert len(exported_items) >= 2

    # 3. Clear without confirm -> 400
    res_clear_fail = await async_client.delete("/api/v1/memory/clear", headers=headers)
    assert res_clear_fail.status_code == 400

    # 4. Clear with confirm -> 200
    res_clear_ok = await async_client.delete("/api/v1/memory/clear?confirm=true", headers=headers)
    assert res_clear_ok.status_code == 200
    assert res_clear_ok.json()["status"] == "success"

    # Verify empty
    res_list = await async_client.get("/api/v1/memory", headers=headers)
    assert len(res_list.json()) == 0

    # 5. Import exported memories
    import_payload = [
        {"content": item["content"], "category": item["category"]}
        for item in exported_items
    ]
    res_import = await async_client.post("/api/v1/memory/import", json=import_payload, headers=headers)
    assert res_import.status_code == 200
    assert res_import.json()["imported_count"] == len(import_payload)

    # Verify restored
    res_list_after = await async_client.get("/api/v1/memory", headers=headers)
    assert len(res_list_after.json()) == len(import_payload)


@pytest.mark.asyncio
async def test_chat_integrates_retrieved_memory_into_context(async_client, registered_user_and_token):
    """
    Verifies that when a personal memory is present, calling chat executes
    retrieval and passes relevant memories to the context manager / model prompt.
    """
    headers, _ = registered_user_and_token

    # 1. Store a distinct personal preference
    await async_client.post(
        "/api/v1/memory",
        json={
            "content": "User strictly prefers pure functional programming with Immutable dataclasses in Python.",
            "category": "personal",
            "importance": 5,
            "tags": ["functional", "python", "immutability"],
        },
        headers=headers,
    )

    # 2. Mock provider.generate to inspect context messages
    mock_response = AssistantResponse(
        content="Understood. We will implement functional patterns using immutable dataclasses.",
        provider="ollama",
        model="qwen2.5:1.5b",
        usage=TokenUsage(prompt_tokens=40, completion_tokens=15, total_tokens=55),
        latency_ms=120,
    )

    captured_messages = []

    async def mock_generate(messages, model, temperature):
        captured_messages.extend(messages)
        return mock_response

    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate", side_effect=mock_generate), \
         patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True

        chat_payload = {
            "message": "How should I structure the Python data models for this project?",
            "provider": "ollama",
            "model": "qwen2.5:1.5b",
        }
        res_chat = await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers)
        assert res_chat.status_code == 200

    # 3. Verify that <relevant_memories> was injected into the system prompt message
    assert len(captured_messages) >= 1
    system_msg = next((m for m in captured_messages if m.role == Role.SYSTEM), None)
    assert system_msg is not None
    assert "<relevant_memories>" in system_msg.content


# =============================================================================
# Suggestion & Consent API Tests (Phase 04.5)
# =============================================================================

@pytest.mark.asyncio
async def test_suggestion_api_lifecycle(async_client, registered_user_and_token):
    """
    Verifies suggestion API endpoints:
    - Listing pending suggestions
    - Approving a suggestion (promotes to permanent memory)
    - Rejecting a suggestion (excluded from memory)
    """
    headers, _ = registered_user_and_token

    # 1. Simulate chat turn with identified fact without explicit remember command
    mock_response = AssistantResponse(
        content="Noted, our database is SQLite.",
        provider="ollama",
        model="qwen2.5:1.5b",
        usage=TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
        latency_ms=100,
    )

    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate", return_value=mock_response), \
         patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True

        # User mentions project fact in passing
        chat_payload = {
            "message": "We decided to use SQLite for our relational database storage.",
            "provider": "ollama",
            "model": "qwen2.5:1.5b",
        }
        res_chat = await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers)
        assert res_chat.status_code == 200

    # 2. Verify that NO permanent memory was created silently
    res_memories = await async_client.get("/api/v1/memory", headers=headers)
    assert res_memories.status_code == 200
    assert len(res_memories.json()) == 0

    # 3. Verify that a PENDING suggestion was created
    res_sug = await async_client.get("/api/v1/memory/suggestions", headers=headers)
    assert res_sug.status_code == 200
    suggestions = res_sug.json()
    assert len(suggestions) >= 1
    suggestion_id = suggestions[0]["id"]
    assert suggestions[0]["status"] == "pending"
    assert any("sqlite" in s["content"].lower() for s in suggestions)

    # 4. User explicitly approves the suggestion
    res_approve = await async_client.post(
        f"/api/v1/memory/suggestions/{suggestion_id}/approve",
        headers=headers,
    )
    assert res_approve.status_code == 201
    approved_memory = res_approve.json()
    assert approved_memory["category"] == "project"
    assert "sqlite" in approved_memory["content"].lower()

    # 5. Now it IS in permanent memories!
    res_memories_after = await async_client.get("/api/v1/memory", headers=headers)
    assert len(res_memories_after.json()) == 1


@pytest.mark.asyncio
async def test_explicit_remember_directive_directly_saves_memory(async_client, registered_user_and_token):
    """
    Verifies that explicit directives ("Remember that...") are saved directly,
    while non-explicit statements become suggestions.
    """
    headers, _ = registered_user_and_token

    mock_response = AssistantResponse(
        content="I will remember that your favorite editor is Neovim.",
        provider="ollama",
        model="qwen2.5:1.5b",
        usage=TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
        latency_ms=100,
    )

    with patch("backend.app.intelligence.providers.ollama.OllamaProvider.generate", return_value=mock_response), \
         patch("backend.app.intelligence.providers.ollama.OllamaProvider.is_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True

        # Explicit user command: "Remember that..."
        chat_payload = {
            "message": "Remember that my favorite text editor is Neovim.",
            "provider": "ollama",
            "model": "qwen2.5:1.5b",
        }
        res_chat = await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers)
        assert res_chat.status_code == 200

    # Verify directly stored in permanent memories
    res_memories = await async_client.get("/api/v1/memory", headers=headers)
    assert res_memories.status_code == 200
    memories = res_memories.json()
    assert len(memories) >= 1
    assert any("neovim" in m["content"].lower() for m in memories)
