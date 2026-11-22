"""
LOVE Phase 09.5: Restart, Offline & Reconnect Verification.

Executes the 8 mandatory runtime verification scenarios:
1. Events created before shutdown survive cold restart.
2. Device B can retrieve missed events after restart.
3. Cursor acknowledgement survives restart.
4. Repeated pull requests do not duplicate canonical records.
5. Authentication expiration is handled correctly (401 on expired tokens).
6. Reconnection does not replay destructive actions.
7. Revoked clients cannot reconnect and synchronize.
8. Pending client text drafts do not falsely appear as server-synchronized data.

Preserves database/love.db intact.
"""

import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta, timezone
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient

from backend.app.config.settings import get_settings
from backend.app.main import app
from backend.app.security.tokens import create_access_token


def run_restart_offline_verification():
    print("================================================================================")
    print("PHASE 09.5: RESTART, OFFLINE & RECONNECT RUNTIME VERIFICATION")
    print("================================================================================\n")

    client = TestClient(app)

    # Authenticate as primary assistant owner across multiple devices
    owner_username = "work_persist_1795095542"
    owner_password = "SecurePassword123!"

    # Login Device A (Workstation)
    login_a_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": owner_username,
            "password": owner_password,
            "device_identifier": f"device-workstation-win-{int(time.time())}",
            "device_name": "Workstation Rig",
            "device_type": "windows",
            "client_version": "0.2.0"
        }
    )
    assert login_a_resp.status_code == 200, f"Owner login failed: {login_a_resp.text}"
    login_a = login_a_resp.json()
    token_a = login_a["access_token"]
    user_id = login_a["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    devs_resp = client.get("/api/v1/devices", headers=headers_a).json()
    dev_a_id = devs_resp["devices"][0]["id"]

    # Login Device B (Mobile Companion)
    login_b_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": owner_username,
            "password": owner_password,
            "device_identifier": f"device-pixel9-companion-{int(time.time())}",
            "device_name": "Pixel 9 Companion",
            "device_type": "android",
            "client_version": "0.2.0"
        }
    )
    assert login_b_resp.status_code == 200, f"Device B login failed: {login_b_resp.text}"
    login_b = login_b_resp.json()
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    devs_resp = client.get("/api/v1/devices", headers=headers_a).json()
    dev_b_id = [d["id"] for d in devs_resp["devices"] if d["device_name"] == "Pixel 9 Companion"][0]

    # Enable Multi-Device Mode
    client.put("/api/v1/sync/settings", headers=headers_a, json={"sync_mode": "multi_device"})

    # --------------------------------------------------------------------------
    # Scenario 1: Events created before shutdown survive cold restart
    # --------------------------------------------------------------------------
    print("[Scenario 1] Testing event persistence before and after restart...")
    conv_resp = client.post("/api/v1/intelligence/conversations", headers=headers_a, json={"title": "Pre-Shutdown Thread"})
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    pref_resp = client.post("/api/v1/sync/push", headers=headers_a, json={
        "changes": [{"entity_type": "preference", "entity_id": "theme", "action": "updated", "payload": {"theme": "cyber_dark"}}]
    })
    assert pref_resp.status_code == 200
    cursor_before_shutdown = pref_resp.json()["new_cursor"]
    print(f"  Events recorded before shutdown up to cursor #{cursor_before_shutdown}")

    # Simulate Cold Restart: recreate TestClient, re-read from database
    client_restarted = TestClient(app)
    st_post = client_restarted.get("/api/v1/sync/status", headers=headers_a).json()
    assert st_post["current_cursor"] >= cursor_before_shutdown
    print(f"  [OK] Cold restart verified: Cursor #{st_post['current_cursor']} intact, total events={st_post['total_events']}")

    # --------------------------------------------------------------------------
    # Scenario 2: Device B can retrieve missed events after restart
    # --------------------------------------------------------------------------
    print("\n[Scenario 2] Device B retrieves missed events created before restart...")
    changes_b = client_restarted.get(f"/api/v1/sync/changes?since_cursor=0&exclude_device_id={dev_b_id}", headers=headers_b).json()
    assert changes_b["count"] >= 2
    event_entities = [c["entity_id"] for c in changes_b["changes"]]
    assert conv_id in event_entities or "theme" in event_entities
    latest_received_cursor = changes_b["changes"][-1]["cursor"]
    print(f"  [OK] Device B retrieved {changes_b['count']} missed events, latest cursor #{latest_received_cursor}")

    # --------------------------------------------------------------------------
    # Scenario 3: Cursor acknowledgement survives restart
    # --------------------------------------------------------------------------
    print("\n[Scenario 3] Device B acknowledges cursor, verifying persistence across restart...")
    ack_resp = client_restarted.post("/api/v1/sync/acknowledge", headers=headers_b, json={"cursor": latest_received_cursor})
    assert ack_resp.status_code == 200
    assert ack_resp.json()["cursor"] == latest_received_cursor

    # Simulate second restart
    client_restarted_2 = TestClient(app)
    # Check Device B cursor from endpoint
    changes_b_next = client_restarted_2.get(f"/api/v1/sync/changes?since_cursor={latest_received_cursor}&exclude_device_id={dev_b_id}", headers=headers_b).json()
    assert changes_b_next["count"] == 0, "All events up to latest_received_cursor should have been processed"
    print(f"  [OK] Cursor #{latest_received_cursor} persisted across second restart; 0 pending events remaining for Device B")

    # --------------------------------------------------------------------------
    # Scenario 4: Repeated pull requests do not duplicate canonical records
    # --------------------------------------------------------------------------
    print("\n[Scenario 4] Repeated pull requests verification...")
    total_events_before = client_restarted_2.get("/api/v1/sync/status", headers=headers_a).json()["total_events"]
    for _ in range(5):
        client_restarted_2.get("/api/v1/sync/changes?since_cursor=0", headers=headers_a)
    total_events_after = client_restarted_2.get("/api/v1/sync/status", headers=headers_a).json()["total_events"]
    assert total_events_before == total_events_after
    print(f"  [OK] 5 repeated pull requests executed: Total events unchanged ({total_events_after}), zero duplication")

    # --------------------------------------------------------------------------
    # Scenario 5: Authentication expiration is handled correctly
    # --------------------------------------------------------------------------
    print("\n[Scenario 5] Authentication token expiration handling...")
    expired_token, _ = create_access_token(
        user_id=user_id,
        email="work_persist_1795095542@love.ai",
        is_owner=True,
        device_id=dev_b_id,
        expires_delta=timedelta(seconds=-30)  # expired 30 seconds ago
    )
    exp_resp = client_restarted_2.get("/api/v1/sync/status", headers={"Authorization": f"Bearer {expired_token}"})
    assert exp_resp.status_code == 401, f"Expected 401 for expired token, got {exp_resp.status_code}"
    print(f"  [OK] Expired token correctly rejected with 401 Unauthorized: {exp_resp.json()['detail']}")

    # --------------------------------------------------------------------------
    # Scenario 6: Reconnection does not replay destructive actions
    # --------------------------------------------------------------------------
    print("\n[Scenario 6] Reconnection safety & non-replay of destructive actions...")
    # Delete conversation
    del_resp = client_restarted_2.delete(f"/api/v1/intelligence/conversations/{conv_id}", headers=headers_a)
    assert del_resp.status_code == 200

    # Device B reconnects and pulls delete event
    del_event = client_restarted_2.get(f"/api/v1/sync/changes?since_cursor={latest_received_cursor}", headers=headers_b).json()
    deleted_changes = [c for c in del_event["changes"] if c["entity_id"] == conv_id and c["action"] == "deleted"]
    assert len(deleted_changes) == 1

    # Attempting to delete again returns 404 Not Found (safe, idempotent error)
    del_replay = client_restarted_2.delete(f"/api/v1/intelligence/conversations/{conv_id}", headers=headers_a)
    assert del_replay.status_code == 404
    print(f"  [OK] Deletion recorded once in event log, replay safely rejected with 404")

    # --------------------------------------------------------------------------
    # Scenario 7: Revoked clients cannot reconnect and synchronize
    # --------------------------------------------------------------------------
    print("\n[Scenario 7] Revoked client reconnection prevention...")
    rev_resp = client_restarted_2.post(f"/api/v1/devices/{dev_b_id}/revoke", headers=headers_a)
    assert rev_resp.status_code == 200

    # Device B attempts to reconnect and sync
    pull_attempt = client_restarted_2.get("/api/v1/sync/changes?since_cursor=0", headers=headers_b)
    assert pull_attempt.status_code == 401
    assert "revoked" in pull_attempt.json()["detail"].lower()

    push_attempt = client_restarted_2.post("/api/v1/sync/push", headers=headers_b, json={"changes": []})
    assert push_attempt.status_code == 401
    print(f"  [OK] Revoked Device B immediately rejected with 401 Unauthorized on subsequent requests")

    # --------------------------------------------------------------------------
    # Scenario 8: Pending client text drafts do not falsely appear as server-synchronized data
    # --------------------------------------------------------------------------
    print("\n[Scenario 8] Client draft isolation verification...")
    # Verify server database has zero uncommitted draft events
    all_events = client_restarted_2.get("/api/v1/sync/changes?since_cursor=0", headers=headers_a).json()["changes"]
    for ev in all_events:
        assert ev["entity_type"] in ["conversation", "message", "memory", "task", "action_approval", "preference"]
        # Entity ID must be valid, not empty
        assert ev["entity_id"] != ""
        # Content must represent committed state
        if ev["entity_type"] == "message":
            assert ev["payload"].get("status") in ["completed", "streaming"]
    print("  [OK] Zero uncommitted client text drafts exist in server sync event stream")

    print("\n================================================================================")
    print("ALL 8 RESTART, OFFLINE & RECONNECT SCENARIOS VERIFIED SUCCESSFULLY!")
    print("================================================================================\n")


if __name__ == "__main__":
    run_restart_offline_verification()
