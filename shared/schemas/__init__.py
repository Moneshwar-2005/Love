"""
Shared Pydantic Schemas for API contracts and data exchange.
"""

from shared.schemas.auth import (
    LogoutRequest,
    MessageResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from shared.schemas.device import (
    DeviceListResponse,
    DeviceRegisterRequest,
    DeviceResponse,
)
from shared.schemas.health import HealthCheckResponse, ServiceHealthDetail

__all__ = [
    "HealthCheckResponse",
    "ServiceHealthDetail",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "TokenResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "LogoutRequest",
    "MessageResponse",
    "DeviceRegisterRequest",
    "DeviceResponse",
    "DeviceListResponse",
]
