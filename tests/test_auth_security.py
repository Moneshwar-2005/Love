"""
Unit tests for Argon2id password hashing, JWT tokens, and rate limiting.
"""

from datetime import timedelta
import pytest

from backend.app.config.settings import get_settings
from backend.app.security import (
    InvalidTokenError,
    PasswordPolicyError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    login_rate_limiter,
    validate_password_strength,
    verify_password,
)
from shared.constants import TokenType

settings = get_settings()


def test_argon2id_password_hashing():
    """Verify Argon2id produces valid hashes and verifies correctly."""
    password = "SuperSecretPassword123!"
    h1 = hash_password(password)
    h2 = hash_password(password)

    # Argon2id must produce different hashes due to random salting
    assert h1 != h2
    assert h1.startswith("$argon2id$")
    assert h2.startswith("$argon2id$")

    # Correct password verifies
    assert verify_password(password, h1) is True
    assert verify_password(password, h2) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", h1) is False
    assert verify_password("", h1) is False


def test_password_policy_validation():
    """Verify password complexity requirements."""
    # Valid passwords
    validate_password_strength("ValidPass123!")
    validate_password_strength("AnotherStrong99#")

    # Too short
    with pytest.raises(PasswordPolicyError, match="at least 8 characters"):
        validate_password_strength("Short1A")

    # No lowercase
    with pytest.raises(PasswordPolicyError, match="lowercase letter"):
        validate_password_strength("ALLUPPERCASE123!")

    # No uppercase
    with pytest.raises(PasswordPolicyError, match="uppercase letter"):
        validate_password_strength("alllowercase123!")

    # No digits
    with pytest.raises(PasswordPolicyError, match="at least one digit"):
        validate_password_strength("NoDigitsPassword!")


def test_access_token_creation_and_decoding():
    """Verify JWT access token issuance, claims, and validation."""
    user_id = "test-user-uuid-1234"
    email = "test@love.ai"
    token, exp = create_access_token(user_id=user_id, email=email, is_owner=True)

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["is_owner"] is True
    assert payload["type"] == TokenType.ACCESS.value
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert "jti" in payload


def test_refresh_token_creation_and_decoding():
    """Verify JWT refresh token issuance and claims."""
    user_id = "test-user-uuid-5678"
    token, jti, exp = create_refresh_token(user_id=user_id)

    payload = decode_token(token, expected_type=TokenType.REFRESH)
    assert payload["sub"] == user_id
    assert payload["jti"] == jti
    assert payload["type"] == TokenType.REFRESH.value


def test_expired_token_rejection():
    """Verify that expired tokens raise TokenExpiredError."""
    user_id = "test-user-expired"
    token, _ = create_access_token(
        user_id=user_id,
        email="expired@love.ai",
        is_owner=False,
        expires_delta=timedelta(seconds=-10)
    )

    with pytest.raises(TokenExpiredError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_invalid_token_type_rejection():
    """Verify that providing an access token when expecting a refresh token is rejected."""
    token, _ = create_access_token(user_id="user1", email="u@love.ai", is_owner=False)

    with pytest.raises(InvalidTokenError, match="Expected refresh token"):
        decode_token(token, expected_type=TokenType.REFRESH)


def test_tampered_token_rejection():
    """Verify that modified JWT tokens are rejected."""
    token, _ = create_access_token(user_id="user1", email="u@love.ai", is_owner=False)
    tampered = token[:-5] + "XXXXX"

    with pytest.raises(InvalidTokenError):
        decode_token(tampered, expected_type=TokenType.ACCESS)


def test_hash_token():
    """Verify SHA-256 cryptographic hashing of tokens."""
    token = "some-long-random-refresh-token"
    h1 = hash_token(token)
    h2 = hash_token(token)

    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest length
    assert h1 != token


def test_login_rate_limiter():
    """Verify sliding window rate limiting prevents excessive failed login attempts."""
    key = "test-ip-192.168.1.100"
    login_rate_limiter.clear()

    # Initial attempts allowed
    allowed, retry_after = login_rate_limiter.is_allowed(key)
    assert allowed is True
    assert retry_after == 0

    # Record 5 failed attempts
    for _ in range(5):
        login_rate_limiter.record_failure(key)

    # 6th attempt should be blocked
    allowed, retry_after = login_rate_limiter.is_allowed(key)
    assert allowed is False
    assert retry_after > 0

    # Success resets the limiter
    login_rate_limiter.record_success(key)
    allowed, retry_after = login_rate_limiter.is_allowed(key)
    assert allowed is True
