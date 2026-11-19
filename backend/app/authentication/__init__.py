"""
Authentication and User Identity Module for LOVE.
"""

from backend.app.authentication.dependencies import (
    get_current_active_user,
    get_current_owner,
    get_current_user,
    oauth2_scheme,
)
from backend.app.authentication.models import (
    Device,
    RefreshTokenSession,
    User,
    UserCredential,
)
from backend.app.authentication.service import (
    authenticate_user,
    list_user_devices,
    logout_session,
    refresh_session,
    register_or_update_device,
    register_user,
    revoke_user_device,
)

__all__ = [
    "User",
    "UserCredential",
    "Device",
    "RefreshTokenSession",
    "register_user",
    "authenticate_user",
    "refresh_session",
    "logout_session",
    "register_or_update_device",
    "list_user_devices",
    "revoke_user_device",
    "get_current_user",
    "get_current_active_user",
    "get_current_owner",
    "oauth2_scheme",
]
