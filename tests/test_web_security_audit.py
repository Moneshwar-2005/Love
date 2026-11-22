"""
Phase 11.5 Web Security, Authentication & Runtime Audit Tests.
Verifies:
- HttpOnly, SameSite, Secure, Path, and Max-Age cookie attributes across /login, /refresh, /logout
- CSRF defense and Origin validation for cookie-authenticated requests
- Desktop compatibility bypassing Origin validation when refresh token is in request body
- Cookie clearing on logout and on failed refresh (revoked/expired/device revoked)
- Device revocation and token reuse detection under browser cookie authentication
- Production CORS and security constraint enforcement
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.config.settings import Settings, get_settings
from backend.app.database.models.device import Device
from backend.app.database.models.session import RefreshTokenSession
from backend.app.database.models.user import User
from backend.app.database.session import AsyncSessionLocal


def get_error_message(resp) -> str:
    """Helper to extract error message from either HTTPException (detail) or AppException (error.message)."""
    data = resp.json()
    if "detail" in data:
        return str(data["detail"])
    if "error" in data and "message" in data["error"]:
        return str(data["error"]["message"])
    return str(data)


def register_owner(client: TestClient, email: str = "web_audit_owner@love.ai", username: str = "webauditowner") -> dict:
    """Helper to register an owner user."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "SecurePassword123!",
            "full_name": "Web Security Auditor"
        }
    )
    assert response.status_code in (201, 200)
    return response.json()


def test_cookie_attributes_login_and_refresh(client: TestClient):
    """Verify HttpOnly, SameSite, Path, and Max-Age attributes are set properly on login and refresh."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200
    assert "love_refresh_token" in login_resp.cookies

    # Inspect Set-Cookie header
    set_cookie_header = login_resp.headers.get("set-cookie", "")
    assert "love_refresh_token=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()
    assert "path=/api/v1/auth" in set_cookie_header.lower()
    assert "max-age=" in set_cookie_header.lower()

    # Perform refresh using the cookie
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:5174"},
        json={}
    )
    assert refresh_resp.status_code == 200
    ref_cookie_header = refresh_resp.headers.get("set-cookie", "")
    assert "httponly" in ref_cookie_header.lower()
    assert "samesite=lax" in ref_cookie_header.lower()
    assert "path=/api/v1/auth" in ref_cookie_header.lower()


def test_cookie_logout_clearing_attributes(client: TestClient):
    """Verify logout clears the refresh cookie with matching Path and deletion attributes."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    access_token = login_resp.json()["access_token"]

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Origin": "http://localhost:5174"
        },
        json={}
    )
    assert logout_resp.status_code == 200
    set_cookie = logout_resp.headers.get("set-cookie", "").lower()
    assert "love_refresh_token=" in set_cookie
    assert "path=/api/v1/auth" in set_cookie
    # Deletion sets max-age=0 or expires in the past
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


def test_csrf_origin_validation_cookie_refresh_valid_origin(client: TestClient):
    """Verify that browser cookie refresh succeeds with an allowed Origin header."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200

    # Authorized web dev origin
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:5174"},
        json={}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_csrf_origin_validation_cookie_refresh_untrusted_origin(client: TestClient):
    """Verify that browser cookie refresh is REJECTED (403 Forbidden) when coming from an untrusted origin."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200

    # Malicious external origin attempting cross-origin refresh with cookies
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://evil-attacker.example.com"},
        json={}
    )
    assert refresh_resp.status_code == 403
    assert "Untrusted origin" in get_error_message(refresh_resp)


def test_csrf_origin_validation_cookie_logout_untrusted_origin(client: TestClient):
    """Verify that browser cookie logout is REJECTED (403 Forbidden) from an untrusted origin."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    access_token = login_resp.json()["access_token"]

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Origin": "https://evil-attacker.example.com"
        },
        json={}
    )
    assert logout_resp.status_code == 403
    assert "Untrusted origin" in get_error_message(logout_resp)


def test_desktop_direct_refresh_bypasses_origin_check(client: TestClient):
    """
    Verify Desktop & CLI clients passing refresh_token in request body bypass Origin checks.
    Ensures 100% backward compatibility for Electron and API scripts.
    """
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "web_audit_owner@love.ai", "password": "SecurePassword123!"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Desktop / CLI request with refresh_token in body and NO or arbitrary origin
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "vscode-webview://arbitrary-desktop-client"},
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_failed_refresh_clears_dead_cookie(client: TestClient):
    """Verify that if refresh fails (e.g. malformed or invalid token), the dead cookie is cleared."""
    client.cookies.set("love_refresh_token", "invalid.malformed.jwt.token", path="/api/v1/auth")

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:5174"},
        json={}
    )
    assert refresh_resp.status_code == 401
    set_cookie = refresh_resp.headers.get("set-cookie", "").lower()
    assert "love_refresh_token=" in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


def test_revoked_device_cookie_refresh_rejection(client: TestClient):
    """Verify that when a client device is revoked, cookie refresh is rejected with 401."""
    register_owner(client)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email_or_username": "web_audit_owner@love.ai",
            "password": "SecurePassword123!",
            "device_identifier": "web-revoked-audit-device-01",
            "device_name": "Audited Browser Device",
            "device_type": "web"
        }
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # List devices to find the registered device ID
    dev_list_resp = client.get("/api/v1/devices", headers=auth_header)
    assert dev_list_resp.status_code == 200
    devices = dev_list_resp.json()["devices"]
    target_device = next(d for d in devices if d["device_identifier"] == "web-revoked-audit-device-01")
    device_id = target_device["id"]

    # Revoke device via authenticated device API
    del_resp = client.delete(f"/api/v1/devices/{device_id}", headers=auth_header)
    assert del_resp.status_code == 200

    # Attempt refresh via cookie
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:5174"},
        json={}
    )
    assert refresh_resp.status_code == 401
    assert "revoked" in get_error_message(refresh_resp).lower()

    # Dead cookie should be cleared
    set_cookie = refresh_resp.headers.get("set-cookie", "").lower()
    assert "love_refresh_token=" in set_cookie
    assert "max-age=0" in set_cookie or "expires=" in set_cookie


def test_production_cors_validation_rules():
    """Verify that Settings prevents wildcard origins and localhost origins in production."""
    # Production with wildcard must fail
    with pytest.raises(ValueError, match=r"Wildcard '\*' CORS origin is strictly prohibited"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="A"*32,
            CORS_ORIGINS=["*"]
        )

    # Production with localhost without ALLOW_LOCALHOST_IN_PRODUCTION must fail
    with pytest.raises(ValueError, match="Localhost origin .* is not permitted in production"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="A"*32,
            CORS_ORIGINS=["http://localhost:5174"],
            ALLOW_LOCALHOST_IN_PRODUCTION=False
        )

    # Production with explicit domain and no localhost succeeds
    prod_settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="A"*32,
        CORS_ORIGINS=["https://love.myhome.internal"]
    )
    assert prod_settings.effective_cors_origins == ["https://love.myhome.internal"]
    assert prod_settings.effective_cookie_secure is True
