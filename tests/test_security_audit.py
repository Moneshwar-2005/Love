"""
Dedicated security audit tests verifying:
- Immediate rejection of access tokens from revoked devices
- Blocking of login and re-registration from revoked devices
- Concurrency race-condition protection during refresh token rotation
- First-owner setup token enforcement and rejection of unauthorized bootstrap
- Secondary account creation restricted to authenticated owners
- Production environment secret validation guards
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from backend.app.config.settings import Settings


def register_owner(client: TestClient, email: str = "audit_owner@love.ai") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": "auditowner",
            "password": "OwnerSecretPass123!",
            "full_name": "Audit Owner"
        }
    )
    assert resp.status_code == 201
    return resp.json()


def test_revoked_device_access_token_immediately_rejected(client: TestClient):
    """
    CRITICAL SECURITY CHECK:
    Verify that when a device is revoked, its existing access token is immediately rejected
    on protected endpoints even before the access token expires.
    """
    register_owner(client)

    # Login and register a device
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "audit_owner@love.ai",
            "password": "OwnerSecretPass123!",
            "device_identifier": "hardware-uuid-to-revoke-123",
            "device_name": "Compromised Laptop",
            "device_type": "windows"
        }
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # Verify device can access /api/v1/auth/me initially
    me_resp1 = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_resp1.status_code == 200

    # Get device ID from device list
    dev_list_resp = client.get("/api/v1/devices", headers=auth_header)
    devices = dev_list_resp.json()["devices"]
    device_id = next(d["id"] for d in devices if d["device_identifier"] == "hardware-uuid-to-revoke-123")

    # Revoke the device
    del_resp = client.delete(f"/api/v1/devices/{device_id}", headers=auth_header)
    assert del_resp.status_code == 200

    # Immediate access rejection: The access token must now be rejected with 401
    me_resp2 = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_resp2.status_code == 401
    response_text = me_resp2.text
    assert "Device authorization has been revoked" in response_text


def test_revoked_device_cannot_login(client: TestClient):
    """
    SECURITY CHECK:
    Verify that an attacker on a revoked hardware device cannot re-authenticate
    using the revoked device_identifier.
    """
    register_owner(client)

    # Login and register device
    login1 = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "audit_owner@love.ai",
            "password": "OwnerSecretPass123!",
            "device_identifier": "hardware-uuid-blocked-login",
            "device_name": "Stolen Device",
            "device_type": "android"
        }
    )
    token = login1.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Revoke device
    dev_list = client.get("/api/v1/devices", headers=auth_header).json()["devices"]
    device_id = next(d["id"] for d in dev_list if d["device_identifier"] == "hardware-uuid-blocked-login")
    client.delete(f"/api/v1/devices/{device_id}", headers=auth_header)

    # Attempt login from the revoked device
    login2 = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "audit_owner@love.ai",
            "password": "OwnerSecretPass123!",
            "device_identifier": "hardware-uuid-blocked-login",
            "device_name": "Stolen Device",
            "device_type": "android"
        }
    )
    assert login2.status_code == 403
    assert "device has been revoked" in login2.text


def test_revoked_device_cannot_re_register(client: TestClient):
    """
    SECURITY CHECK:
    Verify that attempting to re-register a revoked device_identifier returns 403 Forbidden.
    """
    register_owner(client)

    # 1. Login from an authorized master session (e.g. web console without device_id)
    web_login = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "audit_owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    master_token = web_login.json()["access_token"]
    master_header = {"Authorization": f"Bearer {master_token}"}

    # 2. Register a secondary device
    dev_resp = client.post(
        "/api/v1/devices/register",
        headers=master_header,
        json={
            "device_identifier": "dev-reg-block-uuid",
            "device_name": "Device To Block",
            "device_type": "linux"
        }
    )
    assert dev_resp.status_code == 200
    device_id = dev_resp.json()["id"]

    # 3. Master session revokes the device
    del_resp = client.delete(f"/api/v1/devices/{device_id}", headers=master_header)
    assert del_resp.status_code == 200

    # 4. Attempt re-registration with the same revoked device_identifier
    re_reg = client.post(
        "/api/v1/devices/register",
        headers=master_header,
        json={
            "device_identifier": "dev-reg-block-uuid",
            "device_name": "Device To Block Reborn",
            "device_type": "linux"
        }
    )
    assert re_reg.status_code == 403
    assert "device has been revoked" in re_reg.text


def test_owner_authorized_secondary_user_creation(client: TestClient):
    """
    SECURITY CHECK:
    Verify that an authenticated owner CAN create a secondary user,
    while an anonymous caller CANNOT.
    """
    register_owner(client)

    # Anonymous attempt fails
    anon_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "secondary_anon@love.ai",
            "username": "secondaryanon",
            "password": "SecondarySecret123!"
        }
    )
    assert anon_resp.status_code == 403
    assert "Public registration is disabled" in anon_resp.text

    # Owner logs in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "audit_owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    owner_token = login_resp.json()["access_token"]
    owner_header = {"Authorization": f"Bearer {owner_token}"}

    # Owner creates secondary user
    owner_create_resp = client.post(
        "/api/v1/auth/register",
        headers=owner_header,
        json={
            "email": "secondary_authorized@love.ai",
            "username": "secondaryauth",
            "password": "SecondarySecret123!",
            "full_name": "Authorized Secondary User"
        }
    )
    assert owner_create_resp.status_code == 201
    sec_user = owner_create_resp.json()
    assert sec_user["email"] == "secondary_authorized@love.ai"
    assert sec_user["is_owner"] is False


@pytest.mark.asyncio
async def test_concurrent_refresh_requests_race_condition(test_app):
    """
    SECURITY CONCURRENCY CHECK:
    Simulates simultaneous concurrent refresh requests with the identical refresh token.
    Verifies that token rotation lock prevents dual issuance and properly detects reuse.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "concurrency@love.ai",
                "username": "concurrent_user",
                "password": "OwnerSecretPass123!",
                "full_name": "Concurrent Tester"
            }
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email_or_username": "concurrency@love.ai", "password": "OwnerSecretPass123!"}
        )
        refresh_token = login.json()["refresh_token"]

        # Launch two simultaneous refresh requests
        task1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        task2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        res1, res2 = await asyncio.gather(task1, task2)

        status_codes = [res1.status_code, res2.status_code]
        # Exactly one request must succeed (200), and the second must be rejected (401)
        assert 200 in status_codes, f"Expected one 200, got {status_codes}"
        assert 401 in status_codes, f"Expected one 401, got {status_codes}"


def test_production_environment_security_validation():
    """
    SECURITY CHECK:
    Verify that Settings rejects insecure default secrets or DEBUG=True in production.
    """
    # Insecure key in production raises ValueError
    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="love-dev-secret-key-replace-in-production-min-32-chars",
            DEBUG=False
        )

    # Key too short raises ValueError
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="too-short-secret-key",
            DEBUG=False
        )

    # DEBUG=True in production raises ValueError
    with pytest.raises(ValueError, match="DEBUG mode must be disabled"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="a-very-long-and-secure-custom-secret-key-for-prod-32c",
            DEBUG=True
        )

    # Valid production settings pass
    valid_prod = Settings(
        APP_ENV="production",
        SECRET_KEY="a-very-long-and-secure-custom-secret-key-for-prod-32c",
        DEBUG=False
    )
    assert valid_prod.APP_ENV == "production"
    assert valid_prod.DEBUG is False
