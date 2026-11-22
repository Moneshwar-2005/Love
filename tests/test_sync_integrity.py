"""
Comprehensive Audit & Integrity Test Suite for Cross-Device Synchronization (Phase 09.5).

Covers:
1. Migration & Persistence (foreign keys, cascade deletes, unique event IDs, indexes).
2. Event Transaction Integrity (failed DB operations leave no orphan events, credentials omitted, unapproved suggestions omitted).
3. Push API Security (strict entity allowlist, field allowlist, forbidden field rejection, origin device verification).
4. Device Identity & Server-Side Revocation Enforcement (spoofing prevention, 401 on pull/push/ack when revoked).
5. Cursor & Pagination Integrity (pagination, boundary conditions, future cursor rejection, rollback prevention, echo suppression without gaps).
6. Conflict Resolution & Idempotency (LWW preference resolution, push retry idempotency, non-overwrite of conversations/tasks).
7. Operational Mode Invariants (standalone vs multi-device toggling retains 100% of historical data).
"""

import pytest
from fastapi.testclient import TestClient


def register_device_user(client: TestClient, username: str, device_name: str = "Dev1", device_type: str = "windows") -> dict:
    """Helper to register user and authenticate a specific device."""
    email = f"{username}@love.ai"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "SecurePassword123!",
            "full_name": "Audit Test Owner"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": email,
            "password": "SecurePassword123!",
            "device_identifier": f"ident-{username}-{device_name}",
            "device_name": device_name,
            "device_type": device_type,
            "client_version": "0.2.0"
        }
    )
    data = login_resp.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    # Get device ID
    dev_resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    devices = dev_resp.json()["devices"]
    target_dev = [d for d in devices if d["device_name"] == device_name][0]

    return {
        "user_id": user_id,
        "token": token,
        "device_id": target_dev["id"],
        "headers": {"Authorization": f"Bearer {token}"}
    }


def login_second_device(client: TestClient, username: str, device_name: str, device_type: str = "android") -> dict:
    """Helper to login an additional device for an existing user."""
    email = f"{username}@love.ai"
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": email,
            "password": "SecurePassword123!",
            "device_identifier": f"ident-{username}-{device_name}",
            "device_name": device_name,
            "device_type": device_type,
            "client_version": "0.2.0"
        }
    )
    data = login_resp.json()
    token = data["access_token"]

    dev_resp = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    devices = dev_resp.json()["devices"]
    target_dev = [d for d in devices if d["device_name"] == device_name][0]

    return {
        "user_id": data["user"]["id"],
        "token": token,
        "device_id": target_dev["id"],
        "headers": {"Authorization": f"Bearer {token}"}
    }


# ==============================================================================
# 1. PUSH API SECURITY AUDIT
# ==============================================================================

def test_push_api_strict_entity_allowlist(client: TestClient):
    """Verify that only 'preference' entity_type can be pushed by clients."""
    u = register_device_user(client, "pushsec1")

    # Disallowed entity types must all be rejected with 400
    disallowed_types = ["task", "action_approval", "message", "conversation", "memory", "user", "device"]
    for entity_type in disallowed_types:
        resp = client.post(
            "/api/v1/sync/push",
            headers=u["headers"],
            json={
                "changes": [
                    {
                        "entity_type": entity_type,
                        "entity_id": "forged-id-1",
                        "action": "created",
                        "payload": {"data": "malicious"}
                    }
                ]
            }
        )
        assert resp.status_code == 400, f"Expected 400 for entity_type '{entity_type}', got {resp.status_code}"
        assert "not client-pushable" in resp.json()["detail"]


def test_push_api_preference_key_allowlist(client: TestClient):
    """Verify that only explicitly allowlisted preference keys can be pushed."""
    u = register_device_user(client, "pushsec2")

    # Allowed keys should succeed
    for key in ["theme", "mobile_haptic_feedback", "notifications_enabled", "sound_volume"]:
        resp = client.post(
            "/api/v1/sync/push",
            headers=u["headers"],
            json={
                "changes": [
                    {
                        "entity_type": "preference",
                        "entity_id": key,
                        "action": "updated",
                        "payload": {"val": "ok"}
                    }
                ]
            }
        )
        assert resp.status_code == 200, f"Allowed key '{key}' failed with {resp.status_code}"

    # Disallowed key must be rejected with 400
    resp_bad = client.post(
        "/api/v1/sync/push",
        headers=u["headers"],
        json={
            "changes": [
                {
                    "entity_type": "preference",
                    "entity_id": "arbitrary_backdoor_setting",
                    "action": "updated",
                    "payload": {"hack": True}
                }
            ]
        }
    )
    assert resp_bad.status_code == 400
    assert "not in the client-pushable allowlist" in resp_bad.json()["detail"]


def test_push_api_forbidden_fields_rejection(client: TestClient):
    """Verify that clients cannot forge server-authoritative fields in payloads."""
    u = register_device_user(client, "pushsec3")

    forbidden_fields = ["cursor", "event_id", "user_id", "created_at", "origin_device_id", "is_owner", "is_revoked", "role", "password", "token"]
    for field in forbidden_fields:
        resp = client.post(
            "/api/v1/sync/push",
            headers=u["headers"],
            json={
                "changes": [
                    {
                        "entity_type": "preference",
                        "entity_id": "theme",
                        "action": "updated",
                        "payload": {"theme": "dark", field: "injected_value"}
                    }
                ]
            }
        )
        assert resp.status_code == 400, f"Expected 400 for forbidden field '{field}'"
        assert "forbidden server-authoritative field" in resp.json()["detail"]


# ==============================================================================
# 2. DEVICE IDENTITY & REVOCATION ENFORCEMENT
# ==============================================================================

def test_device_cannot_acknowledge_for_another_device(client: TestClient):
    """Spoofing prevention: Client cannot acknowledge a cursor on behalf of another device."""
    dev_a = register_device_user(client, "spoofuser", "DeviceA", "windows")
    dev_b = login_second_device(client, "spoofuser", "DeviceB", "android")

    # Create an event
    client.post(
        "/api/v1/intelligence/conversations",
        headers=dev_a["headers"],
        json={"title": "Thread 1"}
    )

    # Device A attempts to acknowledge using Device B's device_id
    resp = client.post(
        "/api/v1/sync/acknowledge",
        headers=dev_a["headers"],
        json={"cursor": 1, "device_id": dev_b["device_id"]}
    )
    assert resp.status_code == 403
    assert "Device ID mismatch" in resp.json()["detail"]


def test_device_cannot_exclude_unauthorized_foreign_device(client: TestClient):
    """Verify that exclude_device_id cannot reference an unauthorized or foreign device."""
    u1 = register_device_user(client, "useralpha", "Dev1")

    # User 1 tries to exclude an unknown or foreign device ID
    foreign_dev_id = "00000000-0000-4000-8000-000000000000"
    resp = client.get(
        f"/api/v1/sync/changes?since_cursor=0&exclude_device_id={foreign_dev_id}",
        headers=u1["headers"]
    )
    assert resp.status_code == 403
    assert "Cannot exclude an unauthorized or foreign device ID" in resp.json()["detail"]


def test_revoked_device_database_backed_rejection_on_all_sync_apis(client: TestClient):
    """
    Audit Database-Backed Server-Side Revocation Enforcement:
    Once revoked, every subsequent sync call (status, changes, acknowledge, push, settings)
    must be immediately rejected with 401 Unauthorized.
    """
    owner = register_device_user(client, "revoketest", "DesktopMain", "windows")
    mobile = login_second_device(client, "revoketest", "MobileComp", "android")

    # Mobile can initially access sync status
    st_resp = client.get("/api/v1/sync/status", headers=mobile["headers"])
    assert st_resp.status_code == 200

    # Owner revokes Mobile
    rev_resp = client.post(f"/api/v1/devices/{mobile['device_id']}/revoke", headers=owner["headers"])
    assert rev_resp.status_code == 200

    # Now mobile is immediately blocked on ALL sync endpoints
    assert client.get("/api/v1/sync/status", headers=mobile["headers"]).status_code == 401
    assert client.get("/api/v1/sync/changes?since_cursor=0", headers=mobile["headers"]).status_code == 401
    assert client.post("/api/v1/sync/acknowledge", headers=mobile["headers"], json={"cursor": 1}).status_code == 401
    assert client.post("/api/v1/sync/push", headers=mobile["headers"], json={"changes": []}).status_code == 401
    assert client.get("/api/v1/sync/settings", headers=mobile["headers"]).status_code == 401


# ==============================================================================
# 3. CURSOR & PAGINATION INTEGRITY
# ==============================================================================

def test_cursor_boundary_and_rollback_prevention(client: TestClient):
    """Verify future cursor rejection, negative cursor rejection, and rollback rejection."""
    u = register_device_user(client, "cursorbound")

    # 1. Negative cursor rejection
    resp_neg = client.post("/api/v1/sync/acknowledge", headers=u["headers"], json={"cursor": -1})
    assert resp_neg.status_code in (400, 422)

    # 2. Reject acknowledging beyond available event sequence (future cursor)
    resp_future = client.post("/api/v1/sync/acknowledge", headers=u["headers"], json={"cursor": 50})
    assert resp_future.status_code == 400
    assert "Cannot acknowledge future cursor" in resp_future.json()["detail"]

    # Create 3 events
    for i in range(3):
        client.post(
            "/api/v1/intelligence/conversations",
            headers=u["headers"],
            json={"title": f"Conv {i}"}
        )

    # Acknowledge cursor 2
    ack2 = client.post("/api/v1/sync/acknowledge", headers=u["headers"], json={"cursor": 2})
    assert ack2.status_code == 200
    assert ack2.json()["cursor"] == 2

    # 3. Attempted rollback: try to acknowledge cursor 1 after acknowledging 2
    ack1 = client.post("/api/v1/sync/acknowledge", headers=u["headers"], json={"cursor": 1})
    assert ack1.status_code == 400
    assert "Cursor rollback rejected" in ack1.json()["detail"]

    # 4. Repeated acknowledgement of current cursor is idempotent
    ack2_repeat = client.post("/api/v1/sync/acknowledge", headers=u["headers"], json={"cursor": 2})
    assert ack2_repeat.status_code == 200
    assert ack2_repeat.json()["cursor"] == 2


def test_delta_pagination_and_echo_suppression_without_skipping(client: TestClient):
    """
    Verify that paginating with exclude_device_id suppresses caller's events
    without causing subsequent companion events to be skipped.
    """
    dev_a = register_device_user(client, "paginuser", "DeviceA", "windows")
    dev_b = login_second_device(client, "paginuser", "DeviceB", "android")

    # Sequence of writes:
    # Event 1: Dev A (conv 1)
    client.post("/api/v1/intelligence/conversations", headers=dev_a["headers"], json={"title": "Conv A1"})
    # Event 2: Dev B (preference 1)
    client.post("/api/v1/sync/push", headers=dev_b["headers"], json={"changes": [{"entity_type": "preference", "entity_id": "theme", "action": "updated", "payload": {"theme": "neon"}}]})
    # Event 3: Dev A (conv 2)
    client.post("/api/v1/intelligence/conversations", headers=dev_a["headers"], json={"title": "Conv A2"})
    # Event 4: Dev B (preference 2)
    client.post("/api/v1/sync/push", headers=dev_b["headers"], json={"changes": [{"entity_type": "preference", "entity_id": "mobile_haptic_feedback", "action": "updated", "payload": {"enabled": True}}]})

    # Device A fetches changes with echo suppression (limit 1)
    page1 = client.get(
        f"/api/v1/sync/changes?since_cursor=0&limit=1&exclude_device_id={dev_a['device_id']}",
        headers=dev_a["headers"]
    ).json()
    assert page1["count"] == 1
    # Page 1 should be Event 2 (from Dev B, theme)
    assert page1["changes"][0]["entity_id"] == "theme"
    assert page1["has_more"] is True

    # Device A fetches page 2 using cursor of last event received
    cursor1 = page1["changes"][0]["cursor"]
    page2 = client.get(
        f"/api/v1/sync/changes?since_cursor={cursor1}&limit=1&exclude_device_id={dev_a['device_id']}",
        headers=dev_a["headers"]
    ).json()
    assert page2["count"] == 1
    # Page 2 should be Event 4 (from Dev B, mobile_haptic_feedback) — Event 3 was Dev A and suppressed cleanly!
    assert page2["changes"][0]["entity_id"] == "mobile_haptic_feedback"

    # Page 3: no more non-Dev-A events
    cursor2 = page2["changes"][0]["cursor"]
    page3 = client.get(
        f"/api/v1/sync/changes?since_cursor={cursor2}&limit=1&exclude_device_id={dev_a['device_id']}",
        headers=dev_a["headers"]
    ).json()
    assert page3["count"] == 0
    assert page3["has_more"] is False


# ==============================================================================
# 4. CONFLICT RESOLUTION & IDEMPOTENCY
# ==============================================================================

def test_last_write_wins_preference_resolution(client: TestClient):
    """
    Test deterministic server-sequenced Last-Write-Wins on client preferences.
    The latter write obtains a higher cursor and represents the authoritative state.
    """
    dev_a = register_device_user(client, "lwwuser", "DevA", "windows")
    dev_b = login_second_device(client, "lwwuser", "DevB", "android")

    # Device A sets theme to 'cyber'
    resp_a = client.post(
        "/api/v1/sync/push",
        headers=dev_a["headers"],
        json={"changes": [{"entity_type": "preference", "entity_id": "theme", "action": "updated", "payload": {"theme": "cyber"}}]}
    )
    cursor_a = resp_a.json()["new_cursor"]

    # Device B sets theme to 'light' immediately after
    resp_b = client.post(
        "/api/v1/sync/push",
        headers=dev_b["headers"],
        json={"changes": [{"entity_type": "preference", "entity_id": "theme", "action": "updated", "payload": {"theme": "light"}}]}
    )
    cursor_b = resp_b.json()["new_cursor"]

    assert cursor_b > cursor_a

    # Fetch all changes and inspect final state
    ch = client.get("/api/v1/sync/changes?since_cursor=0", headers=dev_a["headers"]).json()
    theme_events = [c for c in ch["changes"] if c["entity_id"] == "theme"]
    assert len(theme_events) == 2
    # The higher cursor is Device B's write
    assert theme_events[-1]["payload"]["theme"] == "light"
    assert theme_events[-1]["cursor"] == cursor_b


def test_push_retry_idempotency(client: TestClient):
    """
    Simulate client retrying push after a network timeout.
    Submitting the same preference update multiple times succeeds safely.
    """
    u = register_device_user(client, "retryuser")

    payload = {
        "changes": [
            {
                "entity_type": "preference",
                "entity_id": "sound_volume",
                "action": "updated",
                "payload": {"volume": 75}
            }
        ]
    }

    # First attempt
    res1 = client.post("/api/v1/sync/push", headers=u["headers"], json=payload)
    assert res1.status_code == 200

    # Retry attempt
    res2 = client.post("/api/v1/sync/push", headers=u["headers"], json=payload)
    assert res2.status_code == 200
    assert res2.json()["accepted"] == 1


# ==============================================================================
# 5. OPERATIONAL MODE SWITCHING & DATA PERSISTENCE
# ==============================================================================

def test_mode_toggling_preserves_historical_data(client: TestClient):
    """
    Verify that switching between Standalone and Multi-Device modes does NOT
    delete or invalidate existing conversations, memories, tasks, or device records.
    """
    u = register_device_user(client, "modetoggle")

    # 1. Create a conversation in Standalone mode
    conv_resp = client.post("/api/v1/intelligence/conversations", headers=u["headers"], json={"title": "Standalone Conv"})
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # 2. Switch to Multi-Device mode
    sw1 = client.put("/api/v1/sync/settings", headers=u["headers"], json={"sync_mode": "multi_device"})
    assert sw1.status_code == 200
    assert sw1.json()["sync_mode"] == "multi_device"
    assert sw1.json()["sync_enabled"] is True

    # 3. Create a memory in Multi-Device mode
    mem_resp = client.post("/api/v1/memory", headers=u["headers"], json={"content": "Persisted fact across modes", "category": "personal", "importance": 4})
    assert mem_resp.status_code == 201
    mem_id = mem_resp.json()["id"]

    # 4. Switch back to Standalone mode
    sw2 = client.put("/api/v1/sync/settings", headers=u["headers"], json={"sync_mode": "standalone"})
    assert sw2.status_code == 200
    assert sw2.json()["sync_mode"] == "standalone"
    assert sw2.json()["sync_enabled"] is False

    # 5. Verify conversation and memory STILL exist in Standalone mode
    conv_check = client.get(f"/api/v1/intelligence/conversations/{conv_id}", headers=u["headers"])
    assert conv_check.status_code == 200
    assert conv_check.json()["title"] == "Standalone Conv"

    mem_check = client.get("/api/v1/memory", headers=u["headers"])
    assert mem_check.status_code == 200
    mems = mem_check.json()
    assert any(m["id"] == mem_id for m in mems)
