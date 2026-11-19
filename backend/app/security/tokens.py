"""
JWT access and refresh token generation, validation, and cryptographic hashing.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import jwt

from backend.app.config.settings import get_settings
from backend.app.core.exceptions import AppException
from backend.app.core.logging import get_logger
from shared.constants import TokenType

logger = get_logger("security.tokens")
settings = get_settings()


class TokenError(AppException):
    """Base exception for token operations."""
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message=message, status_code=status_code)


class TokenExpiredError(TokenError):
    """Raised when an expired JWT token is presented."""
    def __init__(self, message: str = "Token has expired.") -> None:
        super().__init__(message=message, status_code=401)


class InvalidTokenError(TokenError):
    """Raised when an invalid, malformed, or untrusted JWT token is presented."""
    def __init__(self, message: str = "Invalid token credentials.") -> None:
        super().__init__(message=message, status_code=401)


def hash_token(token: str) -> str:
    """
    Computes SHA-256 hash of a token string for safe database persistence.
    Plaintext refresh tokens are never stored in the database.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: str,
    email: str,
    is_owner: bool,
    device_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, datetime]:
    """
    Generates a cryptographically signed JWT access token.
    Returns (token_string, expires_at_datetime).
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "is_owner": is_owner,
        "device_id": device_id,
        "type": TokenType.ACCESS.value,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }

    token = jwt.encode(
        payload,
        settings.effective_jwt_secret,
        algorithm=settings.JWT_ALGORITHM
    )
    return token, expire


def create_refresh_token(
    user_id: str,
    device_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Generates a cryptographically signed JWT refresh token.
    Returns (token_string, jti, expires_at_datetime).
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": user_id,
        "device_id": device_id,
        "type": TokenType.REFRESH.value,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }

    token = jwt.encode(
        payload,
        settings.effective_jwt_secret,
        algorithm=settings.JWT_ALGORITHM
    )
    return token, jti, expire


def decode_token(token: str, expected_type: Optional[TokenType] = None) -> Dict[str, Any]:
    """
    Decodes and rigorously validates a JWT token.
    Validates signature, issuer, audience, expiration, and token type claim.
    """
    try:
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
                "require": ["sub", "exp", "iat", "jti", "type"],
            }
        )

        token_type = payload.get("type")
        if expected_type and token_type != expected_type.value:
            raise InvalidTokenError(f"Expected {expected_type.value} token, but got {token_type}.")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError as exc:
        logger.warning(f"Rejected invalid token: {exc}")
        raise InvalidTokenError()
