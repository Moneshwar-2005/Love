"""
Domain-specific exceptions for the Universal Intelligence Layer (Phase 03).
"""

from typing import Optional
from backend.app.core.exceptions import AppException


class IntelligenceException(AppException):
    """Base exception for all Universal Intelligence Layer errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class ProviderUnavailableError(IntelligenceException):
    """Raised when an AI provider endpoint is unreachable, timed out, or offline."""
    def __init__(self, provider: str, message: Optional[str] = None, details: Optional[dict] = None):
        msg = message or f"AI Provider '{provider}' is currently offline or unreachable."
        super().__init__(message=msg, status_code=503, details=details or {"provider": provider})


class ProviderNotConfiguredError(IntelligenceException):
    """Raised when an AI provider is requested but required credentials or config are missing."""
    def __init__(self, provider: str, message: Optional[str] = None):
        msg = message or f"AI Provider '{provider}' is not configured. Missing required API credentials or endpoint URL."
        super().__init__(message=msg, status_code=400, details={"provider": provider})


class ModelNotFoundError(IntelligenceException):
    """Raised when a specified model cannot be found in the provider registry or local engine."""
    def __init__(self, model: str, provider: Optional[str] = None):
        msg = f"Model '{model}' is not available" + (f" on provider '{provider}'." if provider else ".")
        super().__init__(message=msg, status_code=404, details={"model": model, "provider": provider})


class LocalOnlyViolationError(IntelligenceException):
    """Raised when an operation would route to a cloud model in violation of strict local-only policy."""
    def __init__(self, message: Optional[str] = None):
        msg = message or "Strict Local-Only privacy constraint is active. Cloud model routing is strictly prohibited."
        super().__init__(message=msg, status_code=403, details={"policy": "local_only"})


class ContextLengthExceededError(IntelligenceException):
    """Raised when conversation history and prompt exceed the model's context window limit."""
    def __init__(self, token_count: int, max_tokens: int):
        msg = f"Context length of {token_count} tokens exceeds maximum model capacity of {max_tokens} tokens."
        super().__init__(message=msg, status_code=400, details={"token_count": token_count, "max_tokens": max_tokens})


class StreamingInterruptedError(IntelligenceException):
    """Raised when a streaming response is interrupted by network failure or client disconnect."""
    def __init__(self, message: str = "Streaming generation was interrupted before completion."):
        super().__init__(message=message, status_code=500)


class ConversationNotFoundError(IntelligenceException):
    """Raised when a requested conversation is missing or does not belong to the user."""
    def __init__(self, conversation_id: str):
        super().__init__(
            message=f"Conversation '{conversation_id}' was not found or access is denied.",
            status_code=404,
            details={"conversation_id": conversation_id}
        )
