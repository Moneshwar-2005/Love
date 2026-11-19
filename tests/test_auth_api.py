"""
Integration tests for authentication API endpoints:
- User registration (initial owner setup)
- Duplicate prevention
- Login with email and username
- Failure handling (constant time, generic messages)
- Current user profile (/me)
- Token refresh and rotation
- Token reuse detection
- Logout and session revocation
"""

import pytest
from fastapi.testclient import TestClient


def register_owner(client: TestClient, email: str = "owner@love.ai", username: str = "loveowner") -> dict:
    """Helper to register the initial owner."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "OwnerSecretPass123!",
            "full_name": "Primary Owner"
        }
    )
    assert response.status_code == 201
    return response.json()


def test_first_user_registration_becomes_owner(client: TestClient):
    """Verify first registered account automatically becomes the primary owner."""
    data = register_owner(client)
    assert data["email"] == "owner@love.ai"
    assert data["username"] == "loveowner"
    assert data["is_owner"] is True
    assert data["is_verified"] is True
    assert data["is_active"] is True
    assert "id" in data


def test_duplicate_email_registration_fails(client: TestClient):
    """Verify duplicate email registration returns 409 Conflict."""
    register_owner(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@love.ai",
            "username": "differentusername",
            "password": "AnotherSecret123!"
        }
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["error"]["message"]


def test_duplicate_username_registration_fails(client: TestClient):
    """Verify duplicate username returns 409 Conflict."""
    register_owner(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@love.ai",
            "username": "loveowner",
            "password": "AnotherSecret123!"
        }
    )
    assert response.status_code == 409
    assert "Username is already taken" in response.json()["error"]["message"]


def test_public_registration_disabled_after_owner_created(client: TestClient):
    """Verify that once an owner exists, subsequent registrations return 403 Forbidden."""
    register_owner(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "secondary@love.ai",
            "username": "secondaryuser",
            "password": "SecondaryPass123!"
        }
    )
    assert response.status_code == 403
    assert "Public registration is disabled" in response.json()["error"]["message"]


def test_login_success_with_email_and_username(client: TestClient):
    """Verify user can authenticate using either email or username."""
    register_owner(client, email="alice@love.ai", username="alice_in_wonderland")

    # 1. Login with email
    resp_email = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "alice@love.ai",
            "password": "OwnerSecretPass123!",
            "device_identifier": "test-device-uuid-001",
            "device_name": "Alice Laptop",
            "device_type": "macos"
        }
    )
    assert resp_email.status_code == 200
    data_email = resp_email.json()
    assert "access_token" in data_email
    assert "refresh_token" in data_email
    assert data_email["token_type"] == "Bearer"
    assert data_email["expires_in"] > 0
    assert data_email["user"]["email"] == "alice@love.ai"

    # 2. Login with username
    resp_user = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "alice_in_wonderland",
            "password": "OwnerSecretPass123!"
        }
    )
    assert resp_user.status_code == 200
    assert "access_token" in resp_user.json()


def test_login_failure_invalid_credentials(client: TestClient):
    """Verify failed login returns 401 with generic error message to prevent enumeration."""
    register_owner(client)

    # Wrong password
    resp1 = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "owner@love.ai", "password": "WrongPassword123!"}
    )
    assert resp1.status_code == 401
    assert "Invalid email/username or password" in resp1.json()["error"]["message"]

    # Non-existent email
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "ghost@love.ai", "password": "AnyPassword123!"}
    )
    assert resp2.status_code == 401
    assert "Invalid email/username or password" in resp2.json()["error"]["message"]


def test_current_user_profile_endpoint(client: TestClient):
    """Verify /api/v1/auth/me requires authentication and returns user profile."""
    # Without token
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # Register and login
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    access_token = login_resp.json()["access_token"]

    # With valid token
    resp_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp_auth.status_code == 200
    profile = resp_auth.json()
    assert profile["email"] == "owner@love.ai"
    assert profile["is_owner"] is True


def test_refresh_token_rotation(client: TestClient):
    """Verify token refresh yields new access token and rotated refresh token."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    orig_access = login_resp.json()["access_token"]
    orig_refresh = login_resp.json()["refresh_token"]

    # Refresh
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": orig_refresh}
    )
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()

    new_access = refreshed_data["access_token"]
    new_refresh = refreshed_data["refresh_token"]

    assert new_access != orig_access
    assert new_refresh != orig_refresh

    # Test new access token on protected endpoint
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"}
    )
    assert me_resp.status_code == 200


def test_refresh_token_reuse_detection(client: TestClient):
    """Verify that reusing an already rotated refresh token triggers security revocation."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    orig_refresh = login_resp.json()["refresh_token"]

    # First rotation (succeeds)
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": orig_refresh})
    assert r1.status_code == 200

    # Second rotation with original token (REUSE ATTACK!)
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": orig_refresh})
    assert r2.status_code == 401
    assert "already been used" in r2.json()["error"]["message"]


def test_logout_session_revocation(client: TestClient):
    """Verify logout revokes the refresh token."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "owner@love.ai", "password": "OwnerSecretPass123!"}
    )
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token}
    )
    assert logout_resp.status_code == 200

    # Attempting to refresh with revoked token must fail
    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401
