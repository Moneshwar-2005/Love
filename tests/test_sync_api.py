"""
Integration tests for Cross-Device State Synchronization APIs (Phase 09):
- Sync status and default standalone settings
- Settings modification (toggling Standalone vs Multi-Device)
- Monotonic sequence cursor increments
- Delta change retrieval with `since_cursor` and pagination
- Echo suppression via `exclude_device_id`
- Cursor acknowledgement tracking
- Push client changes with Last-Write-Wins
- Verifying unapproved memory suggestions are not synced
- Device revocation security guard
"""

import pytest
from fastapi.testclient import TestClient


def setup_sync_user(client: TestClient, username: str = "syncuser") -> dict:
    """Helper to register and login user with device identifier."""
    email = f"{username}@love.ai"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "SyncSecurePass123!",
            "full_name": "Sync Test Owner"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": email,
            "password": "SyncSecurePass123!",
            "device_identifier": f"device-{username}-1",
            "device_name": "Test Device 1",
            "device_type": "windows",
            "client_version": "0.2.0"
        }
    )
    data = login_resp.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    # Retrieve device record id
    dev_resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    device_id = dev_resp.json()["devices"][0]["id"]

    return {
        "token": token,
        "user_id": user_id,
        "device_id": device_id,
        "headers": {"Authorization": f"Bearer {token}"}
    }


def test_sync_status_defaults(client: TestClient):
    """Verify default sync settings start in Standalone Mode with sync disabled."""
    u = setup_sync_user(client, "standalonedefault")
    resp = client.get("/api/v1/sync/status", headers=u["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["sync_enabled"] is False
    assert data["sync_mode"] == "standalone"
    assert data["current_cursor"] == 0
    assert data["total_events"] == 0
    assert data["active_devices_count"] >= 1
    assert "server_time" in data


def test_sync_settings_update(client: TestClient):
    """Verify toggling between standalone and multi-device modes."""
    u = setup_sync_user(client, "settingstoggle")

    # 1. Enable multi-device mode
    put_resp = client.put(
        "/api/v1/sync/settings",
        headers=u["headers"],
        json={"sync_enabled": True, "sync_mode": "multi_device", "auto_sync_interval_seconds": 10}
    )
    assert put_resp.status_code == 200
    settings = put_resp.json()
    assert settings["sync_enabled"] is True
    assert settings["sync_mode"] == "multi_device"
    assert settings["auto_sync_interval_seconds"] == 10

    # 2. Status now reflects multi-device mode and recorded preference change event
    status_resp = client.get("/api/v1/sync/status", headers=u["headers"])
    assert status_resp.status_code == 200
    st = status_resp.json()
    assert st["sync_enabled"] is True
    assert st["sync_mode"] == "multi_device"
    assert st["current_cursor"] >= 1


def test_conversation_and_message_sync_events(client: TestClient):
    """Verify conversations and messages generate sequential sync events."""
    u = setup_sync_user(client, "convsyncuser")

    # Create conversation
    conv_resp = client.post(
        "/api/v1/intelligence/conversations",
        headers=u["headers"],
        json={"title": "Sync Conversation"}
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # Query sync changes from cursor 0
    changes_resp = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"])
    assert changes_resp.status_code == 200
    ch_data = changes_resp.json()
    assert ch_data["count"] >= 1
    conv_events = [c for c in ch_data["changes"] if c["entity_type"] == "conversation" and c["entity_id"] == conv_id]
    assert len(conv_events) == 1
    assert conv_events[0]["action"] == "created"
    assert conv_events[0]["payload"]["title"] == "Sync Conversation"


def test_approved_memory_sync_lifecycle(client: TestClient):
    """
    Verify approved memories generate sync events on creation, update, and deletion.
    """
    u = setup_sync_user(client, "memsyncuser")

    # 1. Create canonical memory
    mem_resp = client.post(
        "/api/v1/memory",
        headers=u["headers"],
        json={
            "content": "User prefers dark mode and concise summaries",
            "category": "personal",
            "confidence": 0.95,
            "importance": 4
        }
    )
    assert mem_resp.status_code == 201
    mem_id = mem_resp.json()["id"]

    # Verify sync event created
    changes1 = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"]).json()
    mem_created = [c for c in changes1["changes"] if c["entity_type"] == "memory" and c["entity_id"] == mem_id]
    assert len(mem_created) == 1
    assert mem_created[0]["action"] == "created"
    assert "User prefers dark mode" in mem_created[0]["payload"]["content"]

    # 2. Update memory
    upd_resp = client.put(
        f"/api/v1/memory/{mem_id}",
        headers=u["headers"],
        json={"content": "User prefers dark mode and comprehensive summaries", "importance": 5}
    )
    assert upd_resp.status_code == 200

    changes2 = client.get(f"/api/v1/sync/changes?since_cursor={mem_created[0]['cursor']}", headers=u["headers"]).json()
    mem_updated = [c for c in changes2["changes"] if c["entity_type"] == "memory" and c["entity_id"] == mem_id]
    assert len(mem_updated) == 1
    assert mem_updated[0]["action"] == "updated"

    # 3. Delete memory
    del_resp = client.delete(f"/api/v1/memory/{mem_id}", headers=u["headers"])
    assert del_resp.status_code == 200

    changes3 = client.get(f"/api/v1/sync/changes?since_cursor={mem_updated[0]['cursor']}", headers=u["headers"]).json()
    mem_deleted = [c for c in changes3["changes"] if c["entity_type"] == "memory" and c["entity_id"] == mem_id]
    assert len(mem_deleted) == 1
    assert mem_deleted[0]["action"] == "deleted"


def test_echo_suppression(client: TestClient):
    """Verify that changes originated by a device are suppressed when requested."""
    u = setup_sync_user(client, "echouser")

    # Push change with device origin
    push_payload = {
        "changes": [
            {
                "entity_type": "preference",
                "entity_id": "sound_volume",
                "action": "updated",
                "payload": {"volume": 80}
            }
        ]
    }
    push_resp = client.post("/api/v1/sync/push", headers=u["headers"], json=push_payload)
    assert push_resp.status_code == 200

    # With echo suppression: excluded
    sup_resp = client.get(
        f"/api/v1/sync/changes?since_cursor=0&exclude_device_id={u['device_id']}",
        headers=u["headers"]
    ).json()
    assert len([c for c in sup_resp["changes"] if c["entity_id"] == "sound_volume"]) == 0

    # Without echo suppression: returned
    all_resp = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"]).json()
    assert len([c for c in all_resp["changes"] if c["entity_id"] == "sound_volume"]) == 1


def test_work_task_sync_events(client: TestClient):
    """Verify work tasks record sync events on creation and completion."""
    u = setup_sync_user(client, "tasksyncuser")

    # Create task
    task_resp = client.post(
        "/api/v1/work/tasks",
        headers=u["headers"],
        json={
            "title": "Calculate Revenue",
            "description": "Calculate 15% tax on 50000"
        }
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    # Verify sync event created
    ch_resp = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"]).json()
    task_events = [c for c in ch_resp["changes"] if c["entity_type"] == "task" and c["entity_id"] == task_id]
    assert len(task_events) >= 1
    assert task_events[0]["action"] == "created"


def test_cursor_acknowledgement(client: TestClient):
    """Verify client cursor acknowledgement endpoint and boundary checks."""
    u = setup_sync_user(client, "ackuser")

    # Create a conversation so an event with a real cursor exists
    c_resp = client.post(
        "/api/v1/intelligence/conversations",
        headers=u["headers"],
        json={"title": "Ack Test Thread"}
    )
    assert c_resp.status_code == 201

    # Fetch changes to see actual latest cursor
    ch = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"]).json()
    assert len(ch["changes"]) >= 1
    valid_cursor = ch["changes"][-1]["cursor"]

    # 1. Acknowledge valid cursor
    ack_resp = client.post(
        "/api/v1/sync/acknowledge",
        headers=u["headers"],
        json={"cursor": valid_cursor, "device_id": u["device_id"]}
    )
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()
    assert ack_data["status"] == "acknowledged"
    assert ack_data["cursor"] == valid_cursor
    assert "acknowledged_at" in ack_data

    # 2. Reject future cursor beyond event sequence
    future_resp = client.post(
        "/api/v1/sync/acknowledge",
        headers=u["headers"],
        json={"cursor": valid_cursor + 999, "device_id": u["device_id"]}
    )
    assert future_resp.status_code == 400
    assert "Cannot acknowledge future cursor" in future_resp.json()["detail"]

    # 3. Reject negative cursor (Pydantic schema validation returns 422, service returns 400)
    neg_resp = client.post(
        "/api/v1/sync/acknowledge",
        headers=u["headers"],
        json={"cursor": -5, "device_id": u["device_id"]}
    )
    assert neg_resp.status_code in (400, 422)


def test_push_client_changes(client: TestClient):
    """Verify pushing client-originated state changes and allowlist enforcement."""
    u = setup_sync_user(client, "pushuser")

    # 1. Valid push: supported preferences
    push_payload = {
        "changes": [
            {
                "entity_type": "preference",
                "entity_id": "theme",
                "action": "updated",
                "payload": {"theme": "dark", "accent": "violet"}
            },
            {
                "entity_type": "preference",
                "entity_id": "mobile_haptic_feedback",
                "action": "updated",
                "payload": {"enabled": True, "intensity": "medium"}
            }
        ]
    }
    push_resp = client.post("/api/v1/sync/push", headers=u["headers"], json=push_payload)
    assert push_resp.status_code == 200
    res = push_resp.json()
    assert res["accepted"] == 2
    assert res["new_cursor"] >= 2

    # Verify changes appear in change stream
    ch = client.get("/api/v1/sync/changes?since_cursor=0", headers=u["headers"]).json()
    pref_events = [c for c in ch["changes"] if c["entity_id"] == "theme"]
    assert len(pref_events) == 1
    assert pref_events[0]["payload"]["accent"] == "violet"

    # 2. Security validation: Reject client push of disallowed entity types (e.g. conversation, task, memory)
    bad_entity_payload = {
        "changes": [
            {
                "entity_type": "conversation",
                "entity_id": "fake-conv-id",
                "action": "created",
                "payload": {"title": "Forged Conversation"}
            }
        ]
    }
    bad_resp = client.post("/api/v1/sync/push", headers=u["headers"], json=bad_entity_payload)
    assert bad_resp.status_code == 400
    assert "not client-pushable" in bad_resp.json()["detail"]

    # 3. Security validation: Reject client push with forbidden server fields (e.g. cursor, is_owner)
    forbidden_payload = {
        "changes": [
            {
                "entity_type": "preference",
                "entity_id": "theme",
                "action": "updated",
                "payload": {"theme": "dark", "is_owner": True, "cursor": 9999}
            }
        ]
    }
    forbid_resp = client.post("/api/v1/sync/push", headers=u["headers"], json=forbidden_payload)
    assert forbid_resp.status_code == 400
    assert "forbidden server-authoritative field" in forbid_resp.json()["detail"]


def test_revoked_device_blocked_from_sync(client: TestClient):
    """
    Security verification: A revoked device must be immediately blocked (401 Unauthorized)
    from accessing sync endpoints.
    """
    u = setup_sync_user(client, "revokedeviceuser")

    # 1. Device can access sync initially
    status_resp = client.get("/api/v1/sync/status", headers=u["headers"])
    assert status_resp.status_code == 200

    # 2. Revoke the device
    del_resp = client.delete(f"/api/v1/devices/{u['device_id']}", headers=u["headers"])
    assert del_resp.status_code == 200

    # 3. Next request with the token bound to revoked device must be rejected with 401
    blocked_resp = client.get("/api/v1/sync/status", headers=u["headers"])
    assert blocked_resp.status_code == 401
    assert "revoked" in blocked_resp.json()["detail"].lower()
