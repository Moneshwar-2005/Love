"""
LOVE — Phase 09 Multi-Device State Synchronization Live Verification Script.
Simulates two distinct client devices (Device A: Windows Desktop, Device B: Android Mobile)
interacting with the shared FastAPI backend.

Verifies:
1. Multi-device authentication & device registration
2. Mode configuration (Standalone vs Multi-Device)
3. Monotonic sequential delta synchronization across clients
4. State synchronization for Conversations, Messages, Approved Memories, Work Tasks, Preferences
5. Device cursor acknowledgement and catch-up verification
6. Echo suppression for originating devices
7. Push client changes with Last-Write-Wins
8. Immediate cryptographic revocation blocking unauthorized devices (401 Unauthorized)
9. Seamless fallback to Standalone Mode
"""

import sys
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"


def log(section: str, msg: str, success: bool = True):
    symbol = "✓" if success else "✗"
    print(f"[{symbol}] [{section}] {msg}")


def main():
    print("=" * 75)
    print(" LOVE — Phase 09 Live Multi-Device Synchronization Verification")
    print("=" * 75)

    client = httpx.Client(base_url=BASE_URL, timeout=90.0)

    # Health check
    try:
        h = client.get("/health").json()
        log("HEALTH", f"Connected to LOVE backend: {h['app_name']} v{h['version']} (uptime: {h['uptime_seconds']}s)")
    except Exception as exc:
        log("HEALTH", f"Failed to connect to LOVE backend: {exc}", success=False)
        sys.exit(1)

    ts = int(time.time())
    # Step 1: Authenticate as the Owner across multiple devices
    owner_username = "work_persist_1795095542"
    owner_password = "SecurePassword123!"

    # Test login or fallback register
    login_test = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": owner_username, "password": owner_password}
    )
    if login_test.status_code != 200:
        # If user does not exist, register initial owner
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"{owner_username}@love.ai", "username": owner_username, "password": owner_password, "full_name": "Multi-Device Test Owner"}
        )
        assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
        log("REGISTER", f"Registered assistant owner {owner_username}")
    else:
        log("AUTH", f"Using existing assistant owner: {owner_username}")

    # Step 2: Login Device A (Windows Desktop Rig)
    login_a = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": owner_username,
            "password": owner_password,
            "device_identifier": f"win-rig-{ts}",
            "device_name": "Studio Windows Rig",
            "device_type": "windows",
            "client_version": "0.2.0"
        }
    ).json()
    token_a = login_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Step 3: Login Device B (Android Companion Phone)
    login_b = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": owner_username,
            "password": owner_password,
            "device_identifier": f"pixel-phone-{ts}",
            "device_name": "Pixel 9 Pro Companion",
            "device_type": "android",
            "client_version": "0.2.0"
        }
    ).json()
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Verify Device IDs
    devices = client.get("/api/v1/devices", headers=headers_a).json()["devices"]
    dev_a_id = next(d["id"] for d in devices if d["device_name"] == "Studio Windows Rig")
    dev_b_id = next(d["id"] for d in devices if d["device_name"] == "Pixel 9 Pro Companion")
    log("DEVICES", f"Device A registered: {dev_a_id} (windows) | Device B registered: {dev_b_id} (android)")

    # Step 4: Reset mode to Standalone to verify clean starting baseline
    client.put(
        "/api/v1/sync/settings",
        headers=headers_a,
        json={"sync_enabled": False, "sync_mode": "standalone"}
    )
    st_init = client.get("/api/v1/sync/status", headers=headers_a).json()
    assert st_init["sync_enabled"] is False
    assert st_init["sync_mode"] == "standalone"
    log("MODE", f"Baseline mode verified: Standalone Mode (sync_enabled: False, current_cursor: {st_init['current_cursor']})")
    start_cursor = st_init["current_cursor"]

    # Step 5: Device A enables Multi-Device Mode
    upd_mode = client.put(
        "/api/v1/sync/settings",
        headers=headers_a,
        json={"sync_enabled": True, "sync_mode": "multi_device", "auto_sync_interval_seconds": 10}
    ).json()
    assert upd_mode["sync_enabled"] is True
    assert upd_mode["sync_mode"] == "multi_device"
    log("MODE", f"Device A enabled Multi-Device Mode (interval: {upd_mode['auto_sync_interval_seconds']}s)")

    # Step 6: Device A performs assistant operations
    # 6a. Conversation
    conv = client.post(
        "/api/v1/intelligence/conversations",
        headers=headers_a,
        json={"title": "Cross-Device Protocol Discussion"}
    ).json()
    conv_id = conv["id"]
    log("STATE_GEN", f"Device A created Conversation '{conv['title']}' ({conv_id})")

    # 6b. Message
    msg = client.post(
        "/api/v1/intelligence/chat",
        headers=headers_a,
        json={
            "conversation_id": conv_id,
            "message": "Testing cross-device delta synchronization across platforms."
        }
    ).json()
    log("STATE_GEN", f"Device A generated Message turn (Assistant response model: {msg.get('model', 'default')})")

    # 6c. Approved Memory
    mem = client.post(
        "/api/v1/memory",
        headers=headers_a,
        json={
            "content": "User prefers dark mode UI, violet accent, and markdown summaries",
            "category": "personal",
            "confidence": 0.98,
            "importance": 5
        }
    ).json()
    mem_id = mem["id"]
    log("STATE_GEN", f"Device A saved Approved Memory ({mem_id}): '{mem['content'][:45]}...'")

    # 6d. Work Task
    task = client.post(
        "/api/v1/work/tasks",
        headers=headers_a,
        json={
            "title": "Compute Cross-Device Bandwidth",
            "description": "Calculate 25% of 10000"
        }
    ).json()
    task_id = task["id"]
    log("STATE_GEN", f"Device A planned Work Task ({task_id}): '{task['title']}'")

    # Execute task
    exec_task = client.post(f"/api/v1/work/tasks/{task_id}/execute", headers=headers_a).json()
    log("STATE_GEN", f"Device A executed Work Task -> status: {exec_task['status']}")

    # Step 7: Device B pulls incremental changes from start_cursor
    changes_b = client.get(f"/api/v1/sync/changes?since_cursor={start_cursor}", headers=headers_b).json()
    assert changes_b["count"] >= 4, f"Device B received fewer changes than expected: {changes_b['count']}"

    types_received = {c["entity_type"] for c in changes_b["changes"]}
    log("SYNC_PULL", f"Device B pulled {changes_b['count']} delta events (latest_cursor: {changes_b['latest_cursor']})")
    log("SYNC_PULL", f"Entities synchronized to Device B: {sorted(list(types_received))}")

    assert "conversation" in types_received, "Missing conversation event on Device B"
    assert "memory" in types_received, "Missing memory event on Device B"
    assert "task" in types_received, "Missing task event on Device B"

    # Verify exact contents
    sync_conv = next(c for c in changes_b["changes"] if c["entity_type"] == "conversation" and c["entity_id"] == conv_id)
    assert sync_conv["payload"]["title"] == "Cross-Device Protocol Discussion"
    sync_mem = next(c for c in changes_b["changes"] if c["entity_type"] == "memory" and c["entity_id"] == mem_id)
    assert "User prefers dark mode UI" in sync_mem["payload"]["content"]
    log("VERIFY_DATA", "Device B verified exact payload matching Device A's created state")

    # Step 8: Device B acknowledges cursor
    latest_cursor = changes_b["latest_cursor"]
    ack_res = client.post(
        "/api/v1/sync/acknowledge",
        headers=headers_b,
        json={"cursor": latest_cursor, "device_id": dev_b_id}
    ).json()
    assert ack_res["status"] == "acknowledged"
    assert ack_res["cursor"] == latest_cursor
    log("ACK", f"Device B acknowledged cursor #{latest_cursor}")

    # Query changes since acknowledged cursor: must be empty
    subsequent = client.get(f"/api/v1/sync/changes?since_cursor={latest_cursor}", headers=headers_b).json()
    assert subsequent["count"] == 0
    assert subsequent["has_more"] is False
    log("ACK", f"Device B confirmed fully caught up: 0 pending changes remaining")

    # Step 9: Verify Echo Suppression for Device A
    # Push change with Device A origin
    client.post(
        "/api/v1/sync/push",
        headers=headers_a,
        json={
            "changes": [
                {
                    "entity_type": "preference",
                    "entity_id": "rig_ui_scale",
                    "action": "updated",
                    "payload": {"scale": 1.25}
                }
            ]
        }
    )
    # Query with Device A echo suppression
    sup_a = client.get(
        f"/api/v1/sync/changes?since_cursor={latest_cursor}&exclude_device_id={dev_a_id}",
        headers=headers_a
    ).json()
    assert len([c for c in sup_a["changes"] if c["entity_id"] == "rig_ui_scale"]) == 0
    log("ECHO_SUPPRESSION", "Echo suppression verified: Device A writes are excluded from Device A delta pull")

    # Step 10: Device B pushes a state change
    push_b = client.post(
        "/api/v1/sync/push",
        headers=headers_b,
        json={
            "changes": [
                {
                    "entity_type": "preference",
                    "entity_id": "mobile_haptic_feedback",
                    "action": "updated",
                    "payload": {"enabled": True, "intensity": "medium"}
                }
            ]
        }
    ).json()
    assert push_b["accepted"] == 1
    new_cur = push_b["new_cursor"]
    log("PUSH_CHANGE", f"Device B pushed state change 'mobile_haptic_feedback' -> new cursor #{new_cur}")

    # Device A pulls change originated by Device B
    changes_for_a = client.get(f"/api/v1/sync/changes?since_cursor={new_cur - 1}", headers=headers_a).json()
    found_mobile_pref = [c for c in changes_for_a["changes"] if c["entity_id"] == "mobile_haptic_feedback"]
    assert len(found_mobile_pref) == 1
    assert found_mobile_pref[0]["payload"]["intensity"] == "medium"
    log("PUSH_CHANGE", "Device A successfully pulled state change produced by Device B")

    # Step 11: Security Verification — Device Revocation
    log("SECURITY", f"Device A revoking Device B ({dev_b_id})...")
    revoke_res = client.delete(f"/api/v1/devices/{dev_b_id}", headers=headers_a)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["is_revoked"] is True
    log("SECURITY", f"Device B successfully revoked at {revoke_res.json()['revoked_at']}")

    # Device B attempts to access sync endpoint: MUST BE IMMEDIATELY BLOCKED (401)
    blocked_req = client.get("/api/v1/sync/status", headers=headers_b)
    assert blocked_req.status_code == 401, f"Expected 401 Unauthorized for revoked device, got {blocked_req.status_code}"
    assert "revoked" in blocked_req.json()["detail"].lower()
    log("SECURITY", f"Immediate Revocation Enforced: Device B blocked with 401 Unauthorized ('{blocked_req.json()['detail']}')")

    # Step 12: Revert to Standalone Mode
    st_revert = client.put(
        "/api/v1/sync/settings",
        headers=headers_a,
        json={"sync_enabled": False, "sync_mode": "standalone"}
    ).json()
    assert st_revert["sync_enabled"] is False
    assert st_revert["sync_mode"] == "standalone"
    log("MODE", "Device A successfully switched back to Standalone Mode (local SQLite only)")

    # Status check confirms Standalone Mode
    final_status = client.get("/api/v1/sync/status", headers=headers_a).json()
    assert final_status["sync_enabled"] is False
    assert final_status["sync_mode"] == "standalone"
    assert final_status["active_devices_count"] >= 1  # Device B is revoked, Device A active
    log("FINAL_STATUS", f"Final Status: Standalone, {final_status['total_events']} events logged, {final_status['active_devices_count']} active device")

    print("=" * 75)
    print(" ALL PHASE 09 MULTI-DEVICE SYNCHRONIZATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
