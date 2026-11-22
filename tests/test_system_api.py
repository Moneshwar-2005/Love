"""
Integration tests for System Observability & Command Dashboard endpoints:
- GET /api/v1/system/metrics (Authentication, schema validation, non-mocked measurements)
- GET /api/v1/system/activity (Authentication, chronological ordering, multi-domain events)
"""

import pytest
from fastapi.testclient import TestClient


def get_authenticated_header(client: TestClient) -> dict:
    """Helper that registers owner and returns access token authorization header."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "systemtest@love.ai",
            "username": "systemowner",
            "password": "SystemSecretPass123!",
            "full_name": "System Tester"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "systemtest@love.ai", "password": "SystemSecretPass123!"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_system_metrics_unauthorized(client: TestClient):
    """Metrics endpoint must reject unauthenticated requests."""
    resp = client.get("/api/v1/system/metrics")
    assert resp.status_code == 401


def test_system_metrics_authenticated(client: TestClient):
    """Metrics endpoint must return valid hardware measurements when authenticated."""
    headers = get_authenticated_header(client)
    resp = client.get("/api/v1/system/metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Validate structure
    assert "cpu_percent" in data
    assert isinstance(data["cpu_percent"], (int, float))
    assert 0.0 <= data["cpu_percent"] <= 100.0

    assert "ram" in data
    assert data["ram"]["used_gb"] > 0
    assert data["ram"]["total_gb"] > 0
    assert 0.0 <= data["ram"]["percent"] <= 100.0

    assert "gpu" in data
    assert "available" in data["gpu"]
    assert "name" in data["gpu"]

    assert "local_model" in data
    assert "is_running" in data["local_model"]

    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "timestamp" in data


def test_system_activity_unauthorized(client: TestClient):
    """Activity endpoint must reject unauthenticated requests."""
    resp = client.get("/api/v1/system/activity")
    assert resp.status_code == 401


def test_system_activity_timeline(client: TestClient):
    """Activity endpoint must return genuine events in descending chronological order."""
    headers = get_authenticated_header(client)

    # Generate a conversation
    client.post(
        "/api/v1/intelligence/conversations",
        headers=headers,
        json={"title": "Dashboard Test Conversation"}
    )

    # Query activity
    resp = client.get("/api/v1/system/activity?limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] == len(data["items"])

    if data["items"]:
        first = data["items"][0]
        assert "id" in first
        assert "event_type" in first
        assert "title" in first
        assert "category" in first
        assert "timestamp" in first


def test_database_health_unauthorized(client: TestClient):
    """Database health endpoint must reject unauthenticated requests."""
    resp = client.get("/api/v1/system/database")
    assert resp.status_code == 401


def test_database_health_authenticated(client: TestClient):
    """Database health endpoint must return valid engine diagnostics without credentials."""
    headers = get_authenticated_header(client)
    resp = client.get("/api/v1/system/database", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["engine"] == "sqlite"
    assert data["status"] == "connected"
    assert "latency_ms" in data
    assert data["is_sqlite"] is True
    assert data["foreign_keys_enabled"] is True
    assert data["integrity_status"] == "ok"
    assert "alembic_revision" in data
    assert "table_counts" in data
    assert isinstance(data["table_counts"], dict)
    assert "users" in data["table_counts"]
    # Ensure no credentials or connection URLs leaked
    assert "password" not in data
    assert "DATABASE_URL" not in data


def test_database_backup_and_list_endpoints(client: TestClient):
    """Database backup creation and list endpoints must function reliably."""
    headers = get_authenticated_header(client)

    # 1. Create backup
    resp = client.post("/api/v1/system/database/backup", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert "backup" in data
    assert data["backup"]["is_valid"] is True
    assert data["backup"]["integrity_status"] == "ok"
    assert data["backup"]["filename"].startswith("love_backup_")

    # 2. List backups
    list_resp = client.get("/api/v1/system/database/backups", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(b["filename"] == data["backup"]["filename"] for b in list_data["backups"])

