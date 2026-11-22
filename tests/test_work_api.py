"""
Integration and API Tests for Universal Work Intelligence & Tool Orchestration (Phase 05).
Covers tool discovery, task creation, execution, approval workflow, cancellation,
owner isolation, and chat integration.
"""

import uuid
from unittest.mock import patch
import pytest

from backend.app.work.schemas import ActionStatus, ApprovalState, RiskLevel, TaskStatus


@pytest.fixture
async def registered_user_and_token(async_client):
    """Registers a fresh user and returns the auth headers."""
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"work_user_{uid}@example.com",
        "username": f"work_user_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Work Intelligence Tester",
        "device_identifier": f"work-device-{uid}",
        "device_name": "Test Workstation",
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
    """Registers a second independent user for multi-tenant isolation testing."""
    uid = uuid.uuid4().hex[:8]
    reg_payload = {
        "email": f"second_work_{uid}@example.com",
        "username": f"sec_work_{uid}",
        "password": "SecurePassword123!",
        "full_name": "Second Work User",
        "device_identifier": f"sec-work-device-{uid}",
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


# ==============================================================================
# 1. Tool Discovery API Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_list_tools_api(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # List all available tools
    res = await async_client.get("/api/v1/work/tools", headers=headers)
    assert res.status_code == 200
    tools = res.json()
    assert len(tools) >= 10
    names = [t["name"] for t in tools]
    assert "calculator" in names
    assert "datetime_tool" in names
    assert "workspace_create_file" in names
    assert "workspace_read_file" in names

    # Filter by category
    res_cat = await async_client.get("/api/v1/work/tools?category=math", headers=headers)
    assert res_cat.status_code == 200
    cat_tools = res_cat.json()
    assert len(cat_tools) >= 1
    assert all(t["category"] == "math" for t in cat_tools)


# ==============================================================================
# 2. Task Lifecycle: Immediate Execution (Low Risk)
# ==============================================================================

@pytest.mark.asyncio
async def test_create_and_auto_execute_math_task(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    payload = {
        "description": "Calculate 35 * 40 + 200",
        "title": "Math Computation Task",
    }
    res = await async_client.post("/api/v1/work/tasks?auto_execute=true", json=payload, headers=headers)
    assert res.status_code == 201
    task = res.json()

    assert task["status"] == TaskStatus.COMPLETED.value
    assert task["total_steps"] == 1
    assert task["completed_steps"] == 1
    assert "1600" in task["result_summary"]
    assert len(task["actions"]) == 1
    assert task["actions"][0]["status"] == ActionStatus.COMPLETED.value


# ==============================================================================
# 3. Task Approval Workflow (Medium Risk File Creation)
# ==============================================================================

@pytest.mark.asyncio
async def test_task_approval_and_resumption_workflow(async_client, registered_user_and_token, tmp_path, monkeypatch):
    from backend.app.work.tools import file_tools
    test_ws = tmp_path / "work_api_ws"
    test_ws.mkdir()
    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: test_ws)

    headers, _ = registered_user_and_token

    # 1. Create a task that modifies workspace (medium risk)
    payload = {
        "description": "Create a file called release.json with content {\"version\": \"1.0.0\"}",
        "title": "Create Release File",
    }
    res = await async_client.post("/api/v1/work/tasks?auto_execute=true", json=payload, headers=headers)
    assert res.status_code == 201
    task = res.json()

    # Must be waiting for approval
    assert task["status"] == TaskStatus.AWAITING_APPROVAL.value
    assert len(task["actions"]) == 1
    action = task["actions"][0]
    assert action["status"] == ActionStatus.AWAITING_APPROVAL.value
    assert action["approval_state"] == ApprovalState.PENDING.value
    action_id = action["id"]

    # 2. Check pending approvals endpoint
    appr_res = await async_client.get("/api/v1/work/approvals", headers=headers)
    assert appr_res.status_code == 200
    pending_list = appr_res.json()
    assert any(item["action"]["id"] == action_id for item in pending_list)

    # 3. Approve action and auto-resume execution
    approve_res = await async_client.post(
        f"/api/v1/work/approvals/{action_id}?auto_resume=true",
        json={"approved": True, "reason": "Authorized release creation"},
        headers=headers,
    )
    assert approve_res.status_code == 200
    approved_action = approve_res.json()
    assert approved_action["approval_state"] == ApprovalState.APPROVED.value

    # 4. Verify task reached completed status
    task_res = await async_client.get(f"/api/v1/work/tasks/{task['id']}", headers=headers)
    assert task_res.status_code == 200
    updated_task = task_res.json()
    assert updated_task["status"] == TaskStatus.COMPLETED.value
    assert (test_ws / "release.json").exists()


# ==============================================================================
# 4. Action Rejection Workflow
# ==============================================================================

@pytest.mark.asyncio
async def test_action_rejection_workflow(async_client, registered_user_and_token, tmp_path, monkeypatch):
    from backend.app.work.tools import file_tools
    test_ws = tmp_path / "work_api_ws2"
    test_ws.mkdir()
    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: test_ws)

    headers, _ = registered_user_and_token

    payload = {
        "description": "Create a file called secrets.txt with content my_key",
        "title": "Create File Task",
    }
    res = await async_client.post("/api/v1/work/tasks?auto_execute=true", json=payload, headers=headers)
    assert res.status_code == 201
    task = res.json()
    action_id = task["actions"][0]["id"]

    # Reject the action
    reject_res = await async_client.post(
        f"/api/v1/work/approvals/{action_id}?auto_resume=true",
        json={"approved": False, "reason": "Operation denied by user"},
        headers=headers,
    )
    assert reject_res.status_code == 200
    rejected_action = reject_res.json()
    assert rejected_action["approval_state"] == ApprovalState.REJECTED.value

    # Verify task failed due to user rejection
    task_res = await async_client.get(f"/api/v1/work/tasks/{task['id']}", headers=headers)
    assert task_res.status_code == 200
    assert task_res.json()["status"] == TaskStatus.FAILED.value


# ==============================================================================
# 5. Task Cancellation API
# ==============================================================================

@pytest.mark.asyncio
async def test_cancel_task_api(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    payload = {
        "description": "Create a file called unused.txt with content test",
        "title": "To Be Cancelled",
    }
    create_res = await async_client.post("/api/v1/work/tasks?auto_execute=false", json=payload, headers=headers)
    task_id = create_res.json()["id"]

    cancel_res = await async_client.post(f"/api/v1/work/tasks/{task_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == TaskStatus.CANCELLED.value


# ==============================================================================
# 6. Multi-Tenant Owner Isolation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_task_owner_isolation(async_client, registered_user_and_token, second_user_and_token):
    headers_user1, _ = registered_user_and_token
    headers_user2, _ = second_user_and_token

    # User 1 creates task
    create_res = await async_client.post(
        "/api/v1/work/tasks?auto_execute=true",
        json={"description": "Calculate 100 * 5"},
        headers=headers_user1,
    )
    task_id = create_res.json()["id"]

    # User 2 attempts to fetch User 1's task -> 404
    get_res = await async_client.get(f"/api/v1/work/tasks/{task_id}", headers=headers_user2)
    assert get_res.status_code == 404

    # User 2 list tasks does not contain User 1's task
    list_res = await async_client.get("/api/v1/work/tasks", headers=headers_user2)
    assert list_res.status_code == 200
    user2_task_ids = [t["id"] for t in list_res.json()]
    assert task_id not in user2_task_ids


# ==============================================================================
# 7. Chat Integration with Universal Work Intelligence
# ==============================================================================

@pytest.mark.asyncio
async def test_chat_turn_triggers_work_intelligence(async_client, registered_user_and_token):
    headers, _ = registered_user_and_token

    # Send a math calculation request through normal chat
    chat_payload = {
        "message": "Calculate 85 * 20",
    }
    chat_res = await async_client.post("/api/v1/intelligence/chat", json=chat_payload, headers=headers)
    assert chat_res.status_code == 200
    data = chat_res.json()

    # The assistant message should contain the computed outcome (1700)
    assert "1700" in data["assistant_message"]
    assert data["provider"] == "work_intelligence"
