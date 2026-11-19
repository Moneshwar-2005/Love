"""
Core foundational utilities for LOVE.
"""

from backend.app.core.exceptions import (
    AppException,
    ConfigurationError,
    DatabaseConnectionError,
    EntityNotFoundError,
    register_exception_handlers,
)
from backend.app.core.logging import get_logger, setup_logging

__all__ = [
    "AppException",
    "ConfigurationError",
    "DatabaseConnectionError",
    "EntityNotFoundError",
    "register_exception_handlers",
    "get_logger",
    "setup_logging",
]
