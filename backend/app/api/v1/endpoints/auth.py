"""
Authentication and user identity API endpoints.
Provides user registration, login, token refresh, logout, and profile management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import get_current_active_user
from backend.app.authentication.service import (
    authenticate_user,
    logout_session,
    refresh_session,
    register_user,
)
from backend.app.database.models.user import User
from backend.app.database.session import get_db
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

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register User / Initialize Owner",
    description="Registers a new user account. The first registered account automatically becomes the Assistant Owner. Subsequent registrations are disabled unless open registration is enabled."
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register initial owner or subsequent user."""
    user = await register_user(db=db, request=request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates credentials, optionally registers or updates the client device, and returns JWT access and refresh tokens."
)
async def login(
    request: UserLoginRequest,
    http_request: Request,
    user_agent: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticate credentials and issue tokens."""
    client_ip = http_request.client.host if http_request.client else "127.0.0.1"
    user, device, access_token, refresh_token, expires_in = await authenticate_user(
        db=db,
        request=request,
        client_ip=client_ip,
        user_agent=user_agent
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Rotates the refresh token and returns a new access token and rotated refresh token. Detects token reuse attacks."
)
async def refresh(
    request: TokenRefreshRequest,
    http_request: Request,
    user_agent: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> TokenRefreshResponse:
    """Rotate refresh token and issue new token pair."""
    client_ip = http_request.client.host if http_request.client else "127.0.0.1"
    new_access_token, new_refresh_token, expires_in = await refresh_session(
        db=db,
        refresh_token_str=request.refresh_token,
        client_ip=client_ip,
        user_agent=user_agent
    )

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=expires_in
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout User",
    description="Terminates the session and revokes the associated refresh token."
)
async def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Revoke refresh token and terminate session."""
    await logout_session(
        db=db,
        user_id=current_user.id,
        refresh_token_str=request.refresh_token
    )
    return MessageResponse(message="Successfully logged out and session revoked.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns profile information for the currently authenticated user."
)
async def get_me(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """Retrieve profile of authenticated user."""
    return UserResponse.model_validate(current_user)
