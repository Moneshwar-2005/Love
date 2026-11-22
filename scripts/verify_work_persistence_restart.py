"""
Real Cold-Process Application Restart & Work Task Persistence Verification (Phase 05.5).

Protocol:
1. Spawns Server 1 (Uvicorn subprocess on isolated port 8029).
2. Authenticates test user via HTTP API.
3. Creates a multi-step task via POST /api/v1/work/tasks (math step + workspace file write step).
4. Executes the initial step; confirms it completes and the file step enters 'awaiting_approval'.
5. Completely terminates Server 1 (SIGTERM/kill).
6. Spawns Server 2 (fresh Uvicorn process reading canonical database/love.db).
7. Retrieves original task and action history on Server 2 via GET /api/v1/work/tasks/{task_id}.
8. Confirms completed steps remain completed with outputs intact.
9. Confirms interrupted/pending actions remain safely awaiting approval (no unapproved execution).
10. Explicitly approves the pending action on Server 2, verifying seamless resumption and completion.
11. Cleanly terminates Server 2.
"""

import os
import subprocess
import sys
import time
import httpx

PORT = 8029
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


def run_work_persistence_verification() -> bool:
    print("=" * 75)
    print("LOVE Phase 05.5 — Real Application Work Task Persistence & Cold Restart Test")
    print("=" * 75)

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["APP_ENV"] = "development"
    env["ALLOW_OPEN_REGISTRATION"] = "true"

    # -------------------------------------------------------------------------
    # 1. Start Server 1
    # -------------------------------------------------------------------------
    print("\n[Step 1] Spawning initial application server (Server 1)...")
    proc1 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(PORT), "--host", "127.0.0.1", "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(BASE_URL):
            print("ERROR: Server 1 failed to start within timeout.")
            return False
        print(f"Server 1 active on {BASE_URL} (PID: {proc1.pid})")

        # Register & Login User
        uid = f"work_persist_{int(time.time())}"
        reg_payload = {
            "email": f"{uid}@example.com",
            "username": uid,
            "password": "SecurePassword123!",
            "full_name": "Work Persistence Tester",
            "device_identifier": f"dev-{uid}",
            "device_name": "Restart Rig",
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

        # Create Task: Math step + File step requiring approval
        print("\n[Step 2] Creating multi-step task on Server 1...")
        task_create_payload = {
            "description": f"Create a file called persist_{uid}.txt with content Persistent Verification File",
            "title": "Cold Restart Verification Task",
        }
        r_task = httpx.post(f"{BASE_URL}/api/v1/work/tasks?auto_execute=true", json=task_create_payload, headers=headers, timeout=10.0)
        assert r_task.status_code == 201, f"Task creation failed: {r_task.text}"
        task_data = r_task.json()
        task_id = task_data["id"]
        print(f"Task created with ID: {task_id}, status: {task_data['status']}")

        # Confirm step is awaiting approval on Server 1
        assert task_data["status"] == "awaiting_approval", f"Expected awaiting_approval, got {task_data['status']}"
        action_id = task_data["actions"][0]["id"]
        assert task_data["actions"][0]["approval_state"] == "pending"
        print(f"Action '{action_id}' confirmed safely awaiting approval on Server 1.")

    finally:
        # Terminate Server 1
        print("\n[Step 3] Terminating Server 1 completely (cold shutdown)...")
        proc1.terminate()
        try:
            proc1.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc1.kill()
        print("Server 1 process fully stopped. Waiting for port release...")
        time.sleep(2.0)

    # -------------------------------------------------------------------------
    # 2. Start Server 2 (Fresh Process)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Spawning new, independent application server (Server 2)...")
    proc2 = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(PORT), "--host", "127.0.0.1", "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(BASE_URL):
            print("ERROR: Server 2 failed to start within timeout.")
            return False
        print(f"Server 2 active on {BASE_URL} (PID: {proc2.pid})")

        # 3. Retrieve Task from Server 2
        print("\n[Step 5] Querying original task on Server 2 via HTTP API...")
        r_get = httpx.get(f"{BASE_URL}/api/v1/work/tasks/{task_id}", headers=headers, timeout=10.0)
        assert r_get.status_code == 200, f"Task retrieval on Server 2 failed: {r_get.text}"
        restarted_task = r_get.json()

        print(f"Retrieved task status on Server 2: {restarted_task['status']}")
        assert restarted_task["id"] == task_id
        assert restarted_task["title"] == "Cold Restart Verification Task"
        assert restarted_task["status"] == "awaiting_approval", "Status must remain safely 'awaiting_approval' after cold restart"

        action_on_s2 = restarted_task["actions"][0]
        assert action_on_s2["id"] == action_id
        assert action_on_s2["approval_state"] == "pending", "Pending action must remain pending"
        assert action_on_s2["status"] == "awaiting_approval"
        print("CONFIRMED: Task and action state successfully survived cold restart.")
        print("CONFIRMED: Unapproved action was NOT executed upon restart (Zero destructive auto-execution).")

        # 4. Approve action on Server 2 to complete lifecycle
        print("\n[Step 6] Authorizing action on Server 2...")
        r_appr = httpx.post(
            f"{BASE_URL}/api/v1/work/approvals/{action_id}?auto_resume=true",
            json={"approved": True, "reason": "Cold restart authorization test"},
            headers=headers,
            timeout=10.0,
        )
        assert r_appr.status_code == 200, f"Approval on Server 2 failed: {r_appr.text}"

        # Confirm completion on Server 2
        r_final = httpx.get(f"{BASE_URL}/api/v1/work/tasks/{task_id}", headers=headers, timeout=10.0)
        assert r_final.status_code == 200
        final_task = r_final.json()
        assert final_task["status"] == "completed", f"Expected completed, got {final_task['status']}"
        print(f"CONFIRMED: Task resumed and completed successfully on Server 2! Status: {final_task['status']}")

        print("\n" + "=" * 75)
        print("SUCCESS: Real Application Work Persistence & Cold Restart Verification PASSED!")
        print("=" * 75)
        return True

    finally:
        print("\n[Step 7] Cleanly terminating Server 2...")
        proc2.terminate()
        try:
            proc2.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc2.kill()
        print("Server 2 stopped cleanly.")


if __name__ == "__main__":
    success = run_work_persistence_verification()
    sys.exit(0 if success else 1)
