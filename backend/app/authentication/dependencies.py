"""
FastAPI authentication dependencies and security guards for protected endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.security.tokens import TokenError, decode_token
from shared.constants import TokenType

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodes and verifies Bearer token, then retrieves the authenticated user from the database.
    Raises 401 Unauthorized if token is missing, invalid, or expired.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except TokenError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token does not exist.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user)
) -> User:
    """Enforces that the current authenticated user is active."""
    return user


async def get_current_owner(
    user: User = Depends(get_current_active_user)
) -> User:
    """
    Enforces that the current user is the primary assistant owner.
    Raises 403 Forbidden for non-owner users.
    """
    if not user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative owner access required."
        )
    return user
