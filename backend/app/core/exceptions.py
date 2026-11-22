"""
Core application exceptions and HTTP error handling for LOVE.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.core.logging import get_logger

logger = get_logger("exceptions")


class AppException(Exception):
    """Base application exception for LOVE domain errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AppException):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DatabaseConnectionError(AppException):
    """Raised when unable to establish or verify database connectivity."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class EntityNotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers standardized exception handlers on the FastAPI application instance.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first_err = errors[0] if errors else {}
        loc = [str(x) for x in first_err.get("loc", [])]
        err_type = str(first_err.get("type", ""))

        if any("username" in l.lower() for l in loc):
            if "pattern" in err_type:
                user_msg = "Please enter a valid username (alphanumeric, underscores, and hyphens only)."
            elif "too_short" in err_type:
                user_msg = "Username must be at least 3 characters."
            else:
                user_msg = "Please enter a valid username."
        elif any("email" in l.lower() for l in loc):
            user_msg = "Please enter a valid email address."
        elif any("password" in l.lower() for l in loc):
            if "too_short" in err_type:
                user_msg = "Password must be at least 8 characters."
            else:
                user_msg = "Please enter a valid password."
        else:
            user_msg = "Please complete the required fields with valid values."

        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {user_msg} (type={err_type}, loc={loc})"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "ValidationError",
                    "message": user_msg,
                    "details": {"field": loc[-1] if loc else "field", "type": err_type},
                    "path": request.url.path,
                }
            }
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            f"Handled application exception on {request.method} {request.url.path}: {exc.message}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details,
                    "path": request.url.path,
                }
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "InternalServerError",
                    "message": "An unexpected internal server error occurred.",
                    "path": request.url.path,
                }
            }
        )
