"""
End-to-End Application-Level Memory Persistence & Restart Verification (Phase 04.5).

Protocol:
1. Start an actual uvicorn server process on an isolated port.
2. Create a memory through the HTTP API.
3. Confirm direct canonical storage in SQLite (database/love.db).
4. Terminate the server process completely.
5. Start a brand new server process (true application restart).
6. Execute a hybrid search query via the HTTP API.
7. Confirm the relevant memory is accurately retrieved.
8. Delete the memory via the HTTP API.
9. Search again and confirm the memory is no longer retrieved.
10. Terminate the server process cleanly.
"""

import os
import sqlite3
import subprocess
import sys
import time
import httpx

PORT = 8019
BASE_URL = f"http://127.0.0.1:{PORT}"
DB_PATH = "database/love.db"


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Polls health endpoint until server is responsive."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{url}/api/v1/health", timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run_persistence_verification():
    print("=" * 70)
    print("LOVE Phase 04.5 — Real Application Persistence & Restart Test")
    print("=" * 70)

    # 1. Launch Server Process 1
    print("\n[Step 1] Spawning initial application server process (uvicorn)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["APP_ENV"] = "development"
    env["ALLOW_OPEN_REGISTRATION"] = "true"

    proc1 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(PORT), "--host", "127.0.0.1", "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(BASE_URL):
            print("ERROR: Server 1 failed to become responsive within timeout.")
            return False
        print(f"Server 1 active on {BASE_URL} (PID: {proc1.pid})")

        # 2. Register & Login User
        uid = f"persist_{int(time.time())}"
        reg_payload = {
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "SecurePassword123!",
            "full_name": "Persistence Verification Lead",
            "device_identifier": f"dev-{uid}",
            "device_name": "Test Rig",
            "device_type": "windows",
        }
        r_reg = httpx.post(f"{BASE_URL}/api/v1/auth/register", json=reg_payload, timeout=10.0)
        assert r_reg.status_code in (200, 201), f"Registration failed: {r_reg.text}"

        login_payload = {
            "email_or_username": reg_payload["username"],
            "password": reg_payload["password"],
            "device_identifier": reg_payload["device_identifier"],
            "device_name": reg_payload["device_name"],
            "device_type": reg_payload["device_type"],
        }
        r_login = httpx.post(f"{BASE_URL}/api/v1/auth/login", json=login_payload, timeout=10.0)
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        token = r_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Authenticated test user successfully.")

        # 3. Create Memory via API
        unique_content = f"DURABLE_TEST_FACT: LOVE personal assistant operates with SQLite persistence across process restarts [UID={uid}]."
        mem_create_payload = {
            "content": unique_content,
            "category": "project",
            "importance": 5,
            "tags": ["persistence_test", "restart", "sqlite"],
        }
        r_create = httpx.post(f"{BASE_URL}/api/v1/memory", json=mem_create_payload, headers=headers, timeout=10.0)
        assert r_create.status_code == 201, f"Memory creation failed: {r_create.text}"
        created_memory = r_create.json()
        memory_id = created_memory["id"]
        print(f"[Step 2] Memory created via API: id={memory_id}")

        # 4. Confirm direct canonical storage in SQLite on disk
        print("\n[Step 3] Inspecting canonical SQLite database on disk...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, category FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None, f"Memory {memory_id} was NOT found in SQLite database!"
        assert row[0] == memory_id
        assert row[1] == unique_content
        print(f"Confirmed canonical record on disk in SQLite: row_id={row[0]}")

    finally:
        # 5. Stop Application Server 1
        print("\n[Step 4] Terminating Server Process 1 (simulating full application shutdown)...")
        proc1.terminate()
        try:
            proc1.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc1.kill()
        print("Server 1 process fully stopped. Port released.")

    # Small cooldown
    time.sleep(1.0)

    # 6. Start BRAND NEW Application Server 2
    print("\n[Step 5] Starting BRAND NEW Server Process 2 (simulating cold boot/restart)...")
    proc2 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(PORT), "--host", "127.0.0.1", "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(BASE_URL):
            print("ERROR: Server 2 failed to become responsive within timeout.")
            return False
        print(f"Server 2 active on {BASE_URL} (PID: {proc2.pid})")

        # 7. Search for the memory in the new process session
        print("\n[Step 6] Executing hybrid memory retrieval query on restarted application...")
        search_payload = {
            "query": f"persistence across process restarts UID={uid}",
            "top_k": 3,
            "min_score": 0.1,
        }
        r_search = httpx.post(f"{BASE_URL}/api/v1/memory/search", json=search_payload, headers=headers, timeout=10.0)
        assert r_search.status_code == 200, f"Search failed: {r_search.text}"
        search_results = r_search.json()

        print(f"Retrieved {len(search_results)} search results.")
        assert len(search_results) >= 1, "Zero memories retrieved after application restart!"
        top_match = search_results[0]
        assert top_match["memory"]["id"] == memory_id, f"Expected {memory_id}, got {top_match['memory']['id']}"
        print(f"[Step 7] Persistence CONFIRMED: Retrieved '{top_match['memory']['content']}' with score={top_match['score']}")

        # 8. Delete the memory
        print("\n[Step 8] Deleting memory via API...")
        r_del = httpx.delete(f"{BASE_URL}/api/v1/memory/{memory_id}", headers=headers, timeout=10.0)
        assert r_del.status_code == 200, f"Delete failed: {r_del.text}"
        print("Memory deleted via API.")

        # 9. Verify it cannot be retrieved anymore
        print("\n[Step 9] Verifying memory is excluded from subsequent searches...")
        r_search2 = httpx.post(f"{BASE_URL}/api/v1/memory/search", json=search_payload, headers=headers, timeout=10.0)
        assert r_search2.status_code == 200
        results2 = r_search2.json()
        assert not any(r["memory"]["id"] == memory_id for r in results2), "Deleted memory was still retrieved!"
        print("Confirmed: Deleted memory cannot be retrieved.")

        # Confirm deleted from SQLite disk
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
        row_del = cursor.fetchone()
        conn.close()
        assert row_del is None, "Memory still exists in SQLite database after deletion!"
        print("Confirmed: Canonical row permanently removed from SQLite database.")

        print("\n" + "=" * 70)
        print("PERSISTENCE & RESTART VERIFICATION: SUCCESS (100% Verified)")
        print("=" * 70)
        return True

    finally:
        # 10. Terminate Server Process 2
        print("\n[Step 10] Terminating Server Process 2...")
        proc2.terminate()
        try:
            proc2.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc2.kill()
        print("Server 2 stopped cleanly.")


if __name__ == "__main__":
    success = run_persistence_verification()
    sys.exit(0 if success else 1)
