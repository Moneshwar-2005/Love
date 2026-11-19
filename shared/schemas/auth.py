"""
Pydantic schemas for authentication and user identity requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shared.constants import DeviceType


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""
    email: EmailStr = Field(..., description="Valid email address")
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-]+$", description="Alphanumeric username handle")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password")
    full_name: Optional[str] = Field(None, max_length=100, description="Display name")
    setup_token: Optional[str] = Field(None, description="Initial owner setup token if configured")


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""
    email_or_username: str = Field(..., min_length=3, max_length=255, description="Email address or username")
    password: str = Field(..., min_length=1, max_length=128, description="User password")
    device_identifier: Optional[str] = Field(None, max_length=128, description="Client hardware/installation identifier")
    device_name: Optional[str] = Field(None, max_length=100, description="Friendly client device name")
    device_type: Optional[DeviceType] = Field(None, description="Platform type")
    client_version: Optional[str] = Field(None, max_length=50, description="Client app version")


class UserResponse(BaseModel):
    """Standard user profile representation."""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_owner: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Access and refresh token response after successful authentication."""
    access_token: str = Field(..., description="JWT Bearer access token")
    refresh_token: str = Field(..., description="JWT refresh token for session renewal")
    token_type: str = Field(default="Bearer", description="OAuth2 token type")
    expires_in: int = Field(..., description="Access token lifespan in seconds")
    user: UserResponse = Field(..., description="Authenticated user profile")


class TokenRefreshRequest(BaseModel):
    """Payload for token renewal."""
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class TokenRefreshResponse(BaseModel):
    """New token pair returned after rotation."""
    access_token: str = Field(..., description="New JWT Bearer access token")
    refresh_token: str = Field(..., description="New rotated JWT refresh token")
    token_type: str = Field(default="Bearer", description="OAuth2 token type")
    expires_in: int = Field(..., description="New access token lifespan in seconds")


class LogoutRequest(BaseModel):
    """Payload for terminating a session."""
    refresh_token: Optional[str] = Field(None, description="Specific refresh token to revoke")


class MessageResponse(BaseModel):
    """Generic status message response."""
    message: str
