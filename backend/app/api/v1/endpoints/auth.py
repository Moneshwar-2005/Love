"""
Authentication and user identity API endpoints.
Provides user registration, login, token refresh, logout, and profile management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import get_settings
from backend.app.authentication.dependencies import (
    get_current_active_user,
    get_optional_current_user,
)
from backend.app.authentication.service import (
    authenticate_user,
    logout_session,
    refresh_session,
    register_user,
)
from backend.app.core.exceptions import AppException
from backend.app.security.tokens import TokenError
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

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


def validate_cookie_request_origin(http_request: Request, is_cookie_auth: bool) -> None:
    """
    Validates Origin / Referer header for browser cookie-authenticated requests.
    Mitigates CSRF without affecting Desktop/CLI clients that pass tokens in request bodies.
    """
    if not is_cookie_auth:
        return

    current_settings = get_settings()
    origin = http_request.headers.get("origin")
    allowed = current_settings.effective_cors_origins
    norm_allowed = [o.rstrip("/") for o in allowed]

    if origin:
        norm_origin = origin.rstrip("/")
        if norm_origin not in norm_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"CSRF protection: Untrusted origin '{origin}' for cookie-authenticated request."
            )
        return

    referer = http_request.headers.get("referer")
    if referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        ref_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        if ref_origin not in norm_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"CSRF protection: Untrusted referer origin '{ref_origin}' for cookie-authenticated request."
            )
        return

    # In production, require Origin or Referer for any cookie-authenticated action
    if current_settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF protection: Origin or Referer header required for cookie-authenticated request."
        )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register User / Initialize Owner",
    description="Registers a new user account. The first registered account automatically becomes the Assistant Owner. Subsequent registrations require Owner authorization unless open registration is enabled."
)
async def register(
    request: UserRegisterRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register initial owner or secondary user."""
    user = await register_user(db=db, request=request, creator=current_user)
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
    http_response: Response,
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

    # Set secure HttpOnly cookie for browser web clients
    http_response.set_cookie(
        key="love_refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE.lower(),
        secure=settings.effective_cookie_secure,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=settings.COOKIE_PATH,
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
    http_response: Response,
    user_agent: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> TokenRefreshResponse:
    """Rotate refresh token and issue new token pair."""
    is_cookie_auth = not bool(request.refresh_token) and bool(http_request.cookies.get("love_refresh_token"))
    validate_cookie_request_origin(http_request, is_cookie_auth)

    client_ip = http_request.client.host if http_request.client else "127.0.0.1"
    refresh_token_candidate = request.refresh_token or http_request.cookies.get("love_refresh_token")
    if not refresh_token_candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required in request body or cookie."
        )

    try:
        new_access_token, new_refresh_token, expires_in = await refresh_session(
            db=db,
            refresh_token_str=refresh_token_candidate,
            client_ip=client_ip,
            user_agent=user_agent
        )
    except (TokenError, AppException) as exc:
        # If refresh failed and client relied on cookie, clear the dead/compromised cookie on the 401 response
        if http_request.cookies.get("love_refresh_token"):
            from fastapi.responses import JSONResponse
            err_resp = JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.__class__.__name__,
                        "message": exc.message,
                        "details": getattr(exc, "details", None),
                        "path": http_request.url.path,
                    }
                }
            )
            err_resp.delete_cookie(
                key="love_refresh_token",
                path=settings.COOKIE_PATH,
                domain=settings.COOKIE_DOMAIN,
                secure=settings.effective_cookie_secure,
                httponly=True,
                samesite=settings.COOKIE_SAMESITE.lower(),
            )
            return err_resp
        raise exc

    # Rotate secure HttpOnly cookie for browser clients
    http_response.set_cookie(
        key="love_refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE.lower(),
        secure=settings.effective_cookie_secure,
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=settings.COOKIE_PATH,
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
    http_request: Request,
    http_response: Response,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Revoke refresh token and terminate session."""
    is_cookie_auth = not bool(request.refresh_token) and bool(http_request.cookies.get("love_refresh_token"))
    validate_cookie_request_origin(http_request, is_cookie_auth)

    token_candidate = request.refresh_token or http_request.cookies.get("love_refresh_token")
    if token_candidate:
        await logout_session(
            db=db,
            user_id=current_user.id,
            refresh_token_str=token_candidate
        )
    http_response.delete_cookie(
        key="love_refresh_token",
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.effective_cookie_secure,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE.lower(),
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
