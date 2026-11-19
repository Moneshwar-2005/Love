"""
Automated tests for health check endpoints.
Verifies application name, version, service status, and database connectivity.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from shared.constants import DatabaseStatus, ServiceStatus
from shared.schemas.health import HealthCheckResponse


def test_health_endpoint_root(client: TestClient):
    """
    Verify the root /health endpoint returns 200 OK with valid health metadata.
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "app_name" in data
    assert "version" in data
    assert "status" in data
    assert "database_status" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data

    assert data["status"] in [ServiceStatus.HEALTHY.value, ServiceStatus.DEGRADED.value]
    assert data["database_status"] == DatabaseStatus.CONNECTED.value
    assert data["uptime_seconds"] >= 0.0

    # Validate against Pydantic schema
    validated = HealthCheckResponse.model_validate(data)
    assert validated.app_name == data["app_name"]


def test_health_endpoint_v1(client: TestClient):
    """
    Verify the versioned /api/v1/health endpoint returns 200 OK.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["app_name"]
    assert data["version"]
    assert data["status"] == ServiceStatus.HEALTHY.value
    assert data["database_status"] == DatabaseStatus.CONNECTED.value
    assert "database" in data["services"]
    assert data["services"]["database"]["status"] == ServiceStatus.HEALTHY.value


def test_root_info_endpoint(client: TestClient):
    """
    Verify the root / endpoint returns basic application identity.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "version" in data
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_health_endpoint_async(async_client: AsyncClient):
    """
    Verify health check works asynchronously with httpx AsyncClient.
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ServiceStatus.HEALTHY.value
    assert data["database_status"] == DatabaseStatus.CONNECTED.value
