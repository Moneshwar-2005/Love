"""
Password security utilities implementing Argon2id password hashing and verification.
Conforms to OWASP Password Storage Guidelines.
"""

import re
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from backend.app.core.exceptions import AppException
from backend.app.core.logging import get_logger

logger = get_logger("security.password")

# Initialize Argon2id password hasher with recommended RFC 9106 / OWASP profile
# Type 2 = Argon2id, time_cost=2, memory_cost=65536 KiB (64 MiB), parallelism=1, hash_len=32
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
)


class PasswordPolicyError(AppException):
    """Raised when a password fails policy complexity requirements."""
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using Argon2id with random per-password salt.
    Never logs or persists the plaintext password.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2id hash in constant time.
    Returns True if valid, False otherwise.
    """
    if not password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception as exc:
        logger.error(f"Unexpected error during password verification: {exc}")
        return False


def validate_password_strength(password: str, min_length: int = 8) -> None:
    """
    Validates password strength against standard complexity guidelines:
    - Minimum length
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one numeric digit
    """
    if len(password) < min_length:
        raise PasswordPolicyError(f"Password must be at least {min_length} characters long.")
    if not re.search(r"[a-z]", password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise PasswordPolicyError("Password must contain at least one digit.")
