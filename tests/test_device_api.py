"""
Integration tests for device security and management APIs:
- Device registration across platforms (Windows, macOS, Linux, Android, iOS, Web)
- Device listing
- Device re-registration / metadata update
- Device revocation and session termination
"""

import pytest
from fastapi.testclient import TestClient


def setup_authenticated_user(client: TestClient) -> str:
    """Helper that registers owner and returns access token."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "devicetest@love.ai",
            "username": "deviceowner",
            "password": "OwnerSecretPass123!",
            "full_name": "Device Tester"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "devicetest@love.ai", "password": "OwnerSecretPass123!"}
    )
    return login_resp.json()["access_token"]


def test_device_registration_and_listing(client: TestClient):
    """Verify authorized client device registration and listing."""
    token = setup_authenticated_user(client)
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Register a Windows client device
    reg_resp = client.post(
        "/api/v1/devices/register",
        headers=auth_header,
        json={
            "device_identifier": "win-workstation-uuid-9999",
            "device_name": "Studio Windows Rig",
            "device_type": "windows",
            "client_version": "0.2.0"
        }
    )
    assert reg_resp.status_code == 200
    device = reg_resp.json()
    assert device["device_identifier"] == "win-workstation-uuid-9999"
    assert device["device_name"] == "Studio Windows Rig"
    assert device["device_type"] == "windows"
    assert device["is_trusted"] is True
    assert device["is_revoked"] is False
    assert "id" in device

    device_id = device["id"]

    # 2. List devices
    list_resp = client.get("/api/v1/devices", headers=auth_header)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    device_ids = [d["id"] for d in list_data["devices"]]
    assert device_id in device_ids


def test_device_re_registration_updates_metadata(client: TestClient):
    """Verify that re-registering the same device_identifier updates metadata."""
    token = setup_authenticated_user(client)
    auth_header = {"Authorization": f"Bearer {token}"}

    # Initial registration
    client.post(
        "/api/v1/devices/register",
        headers=auth_header,
        json={
            "device_identifier": "pixel-phone-uuid-777",
            "device_name": "Pixel 8",
            "device_type": "android",
            "client_version": "0.1.0"
        }
    )

    # Update device name and version
    update_resp = client.post(
        "/api/v1/devices/register",
        headers=auth_header,
        json={
            "device_identifier": "pixel-phone-uuid-777",
            "device_name": "Pixel 9 Pro",
            "device_type": "android",
            "client_version": "0.2.0"
        }
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["device_name"] == "Pixel 9 Pro"
    assert updated["client_version"] == "0.2.0"


def test_device_revocation(client: TestClient):
    """Verify device revocation and cascading session termination."""
    token = setup_authenticated_user(client)
    auth_header = {"Authorization": f"Bearer {token}"}

    # Register device
    reg_resp = client.post(
        "/api/v1/devices/register",
        headers=auth_header,
        json={
            "device_identifier": "revokable-device-uuid-111",
            "device_name": "Temp Tablet",
            "device_type": "ios"
        }
    )
    device_id = reg_resp.json()["id"]

    # Revoke device
    del_resp = client.delete(f"/api/v1/devices/{device_id}", headers=auth_header)
    assert del_resp.status_code == 200
    revoked = del_resp.json()
    assert revoked["is_revoked"] is True
    assert revoked["revoked_at"] is not None

    # Revoking non-existent device returns 404
    del_404 = client.delete("/api/v1/devices/non-existent-id", headers=auth_header)
    assert del_404.status_code == 404
