"""
Domain-specific exceptions for Persistent Personal Memory (Phase 04).
"""

from typing import Optional
from backend.app.core.exceptions import AppException


class MemoryException(AppException):
    """Base exception for all memory subsystem domain errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        super().__init__(message=message, status_code=status_code, details=details)


MemoryError = MemoryException


class MemoryNotFoundError(MemoryException):
    """Raised when a memory record is missing or access is unauthorized."""
    def __init__(self, memory_id: str):
        super().__init__(
            message=f"Memory record '{memory_id}' was not found or access is denied.",
            status_code=404,
            details={"memory_id": memory_id}
        )


class DuplicateMemoryError(MemoryException):
    """Raised when an identical memory record already exists."""
    def __init__(self, existing_id: str):
        super().__init__(
            message=f"A duplicate memory already exists with ID '{existing_id}'.",
            status_code=409,
            details={"existing_id": existing_id}
        )


class SensitiveDataBlockedError(MemoryException):
    """Raised when raw credentials or secrets are detected in memory payload."""
    def __init__(self, detected_category: str):
        super().__init__(
            message=(
                f"Memory creation rejected: raw credentials or secrets detected ({detected_category}). "
                "LOVE is prohibited from permanently persisting unencrypted passwords, API keys, or security tokens."
            ),
            status_code=400,
            details={"blocked_category": detected_category}
        )


class EmbeddingUnavailableError(MemoryException):
    """Raised when an embedding provider fails or is not configured."""
    def __init__(self, provider: str, message: Optional[str] = None):
        msg = message or f"Embedding provider '{provider}' is currently unavailable."
        super().__init__(message=msg, status_code=503, details={"provider": provider})


class LocalOnlyViolationError(MemoryException):
    """Raised when an operation would route to a cloud service in violation of strict local-only policy."""
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message=message or "Strict Local-Only privacy constraint is active. Cloud embedding routing is strictly prohibited.",
            status_code=403,
            details={"policy": "local_only"}
        )


class VectorStoreError(MemoryException):
    """Raised when vector storage index operations fail."""
    def __init__(self, message: str):
        super().__init__(message=f"Vector store error: {message}", status_code=500)
