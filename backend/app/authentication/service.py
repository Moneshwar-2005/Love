"""
Authentication and device management business logic service.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.config.settings import get_settings
from backend.app.core.exceptions import AppException, EntityNotFoundError
from backend.app.core.logging import get_logger
from backend.app.database.models import Device, RefreshTokenSession, User, UserCredential
from backend.app.security import (
    InvalidTokenError,
    RateLimitExceededError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    login_rate_limiter,
    validate_password_strength,
    verify_password,
)
from shared.constants import DeviceType, TokenType
from shared.schemas.auth import UserLoginRequest, UserRegisterRequest
from shared.schemas.device import DeviceRegisterRequest

logger = get_logger("authentication.service")
settings = get_settings()


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to ensure a datetime from database has UTC timezone info."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthenticationError(AppException):
    """Raised for authentication failures with generic messages to prevent user enumeration."""
    def __init__(self, message: str = "Invalid email/username or password.") -> None:
        super().__init__(message=message, status_code=401)


class RegistrationClosedError(AppException):
    """Raised when registration is attempted while closed."""
    def __init__(self, message: str = "Public registration is disabled. LOVE assistant is operating in single-owner mode.") -> None:
        super().__init__(message=message, status_code=403)


async def register_user(db: AsyncSession, request: UserRegisterRequest) -> User:
    """
    Registers a new user. The first user registered automatically becomes the Owner.
    Subsequent registrations require ALLOW_OPEN_REGISTRATION to be enabled.
    """
    # 1. Enforce password complexity
    validate_password_strength(request.password, min_length=settings.PASSWORD_MIN_LENGTH)

    normalized_email = request.email.lower().strip()
    normalized_username = request.username.strip()

    # 2. Check for duplicate email
    email_check = await db.execute(select(User).where(User.email == normalized_email))
    if email_check.scalar_one_or_none():
        raise AppException("Email address is already registered.", status_code=409)

    # 3. Check for duplicate username
    username_check = await db.execute(select(User).where(User.username == normalized_username))
    if username_check.scalar_one_or_none():
        raise AppException("Username is already taken.", status_code=409)

    # 4. Check user count to determine owner status
    user_count_result = await db.execute(select(func.count(User.id)))
    existing_user_count = user_count_result.scalar_one()

    is_first_owner = existing_user_count == 0

    if is_first_owner:
        # Validate bootstrap setup token if configured in settings
        if settings.FIRST_OWNER_SETUP_TOKEN:
            if not request.setup_token or request.setup_token != settings.FIRST_OWNER_SETUP_TOKEN:
                raise AppException(
                    "Invalid or missing setup token required for primary owner initialization.",
                    status_code=403
                )
        is_owner = True
        is_verified = True
        logger.info(f"Registering primary assistant owner: {normalized_email}")
    else:
        if not settings.ALLOW_OPEN_REGISTRATION:
            raise RegistrationClosedError()
        is_owner = False
        is_verified = False
        logger.info(f"Registering secondary user: {normalized_email}")

    # 5. Hash password using Argon2id
    password_hash = hash_password(request.password)

    # 6. Create User and UserCredential records
    user = User(
        email=normalized_email,
        username=normalized_username,
        full_name=request.full_name,
        is_active=True,
        is_verified=is_verified,
        is_owner=is_owner,
    )
    db.add(user)
    await db.flush()  # Populates user.id

    credential = UserCredential(
        user_id=user.id,
        password_hash=password_hash,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    request: UserLoginRequest,
    client_ip: str,
    user_agent: Optional[str] = None
) -> Tuple[User, Optional[Device], str, str, int]:
    """
    Authenticates user credentials, registers/updates device, and issues access & refresh tokens.
    Applies sliding window rate limiting to mitigate brute-force attacks.
    """
    # 1. Rate Limiting Check
    rate_key = f"ip:{client_ip}"
    allowed, retry_after = login_rate_limiter.is_allowed(rate_key)
    if not allowed:
        logger.warning(f"Rate limit exceeded for login attempt from {client_ip}")
        raise RateLimitExceededError(retry_after)

    identifier = request.email_or_username.strip().lower()

    # 2. Query user with credentials
    stmt = (
        select(User)
        .options(selectinload(User.credential))
        .where(
            or_(
                func.lower(User.email) == identifier,
                func.lower(User.username) == identifier
            )
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # 3. Constant-time failure handling to prevent user enumeration
    if not user or not user.credential:
        login_rate_limiter.record_failure(rate_key)
        # Dummy verify to normalize response timing
        verify_password("dummy_password", "$argon2id$v=19$m=65536,t=2,p=1$c29tZXNhbHQ$P2G6RkH")
        raise AuthenticationError()

    if not user.is_active:
        raise AppException("Account has been deactivated. Please contact administrator.", status_code=403)

    # 4. Check account lockout timestamp
    now = datetime.now(timezone.utc)
    locked_until = _ensure_utc(user.credential.locked_until)
    if locked_until and locked_until > now:
        raise AppException("Account is temporarily locked due to multiple failed attempts. Try again later.", status_code=403)

    # 5. Verify Argon2id password hash
    is_valid = verify_password(request.password, user.credential.password_hash)
    if not is_valid:
        login_rate_limiter.record_failure(rate_key)
        user.credential.failed_login_attempts += 1
        if user.credential.failed_login_attempts >= 5:
            from datetime import timedelta
            user.credential.locked_until = now + timedelta(minutes=15)
            logger.warning(f"User account {user.id} temporarily locked due to 5 failed attempts.")
        await db.commit()
        raise AuthenticationError()

    # 6. Successful Authentication - Clear failures
    login_rate_limiter.record_success(rate_key)
    user.credential.failed_login_attempts = 0
    user.credential.locked_until = None
    user.credential.last_login_at = now

    # 7. Device Registration / Lookup (if identifier supplied)
    device: Optional[Device] = None
    if request.device_identifier:
        dev_stmt = select(Device).where(
            Device.user_id == user.id,
            Device.device_identifier == request.device_identifier
        )
        dev_result = await db.execute(dev_stmt)
        device = dev_result.scalar_one_or_none()

        device_name = request.device_name or (device.device_name if device else "Unknown Client")
        device_type = (request.device_type.value if request.device_type else (device.device_type if device else DeviceType.OTHER.value))

        if device:
            device.device_name = device_name
            device.device_type = device_type
            device.client_version = request.client_version or device.client_version
            device.last_ip_address = client_ip
            device.last_seen_at = now
            device.is_revoked = False
            device.revoked_at = None
        else:
            device = Device(
                user_id=user.id,
                device_identifier=request.device_identifier,
                device_name=device_name,
                device_type=device_type,
                client_version=request.client_version,
                last_ip_address=client_ip,
                last_seen_at=now,
                is_trusted=True,
                is_revoked=False,
            )
            db.add(device)
        await db.flush()

    # 8. Token Issuance
    access_token, access_exp = create_access_token(
        user_id=user.id,
        email=user.email,
        is_owner=user.is_owner,
        device_id=device.id if device else None
    )
    refresh_token, jti, refresh_exp = create_refresh_token(
        user_id=user.id,
        device_id=device.id if device else None
    )

    # 9. Store hashed refresh token session
    token_session = RefreshTokenSession(
        user_id=user.id,
        device_id=device.id if device else None,
        jti=jti,
        token_hash=hash_token(refresh_token),
        expires_at=refresh_exp,
        is_revoked=False,
        user_agent=user_agent,
        ip_address=client_ip,
    )
    db.add(token_session)
    await db.commit()

    expires_in_seconds = int((access_exp - now).total_seconds())
    return user, device, access_token, refresh_token, expires_in_seconds


async def refresh_session(
    db: AsyncSession,
    refresh_token_str: str,
    client_ip: str,
    user_agent: Optional[str] = None
) -> Tuple[str, str, int]:
    """
    Validates refresh token, executes token rotation, and detects token reuse attacks.
    If a revoked or already rotated token is presented, all active sessions for the device/user are revoked.
    """
    # 1. Decode and validate token claims (iss, aud, exp, type)
    payload = decode_token(refresh_token_str, expected_type=TokenType.REFRESH)
    jti = payload.get("jti")
    user_id = payload.get("sub")
    device_id = payload.get("device_id")

    if not jti or not user_id:
        raise InvalidTokenError("Malformed refresh token payload.")

    # 2. Look up session by JTI
    stmt = select(RefreshTokenSession).where(RefreshTokenSession.jti == jti)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        logger.warning(f"Refresh attempt with non-existent JTI {jti}")
        raise InvalidTokenError("Session not found or expired.")

    # 3. Token Reuse Detection
    if session.is_revoked:
        logger.critical(
            f"SECURITY ALERT: Refresh token reuse detected! JTI {jti} for user {user_id}. "
            f"Revoking all active sessions for device {device_id or 'unknown'}."
        )
        # Invalidate all active sessions for this device to contain breach
        now = datetime.now(timezone.utc)
        revoke_query = select(RefreshTokenSession).where(
            RefreshTokenSession.user_id == user_id,
            RefreshTokenSession.is_revoked == False
        )
        if device_id:
            revoke_query = revoke_query.where(RefreshTokenSession.device_id == device_id)

        active_sessions = (await db.execute(revoke_query)).scalars().all()
        for s in active_sessions:
            s.is_revoked = True
            s.revoked_at = now
        await db.commit()
        raise InvalidTokenError("Token has already been used or revoked. For your security, all active sessions on this device have been terminated.")

    # 4. Verify token hash
    if session.token_hash != hash_token(refresh_token_str):
        logger.warning(f"Token hash mismatch for JTI {jti}")
        session.is_revoked = True
        session.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        raise InvalidTokenError("Token verification failed.")

    # 5. Check database expiration
    now = datetime.now(timezone.utc)
    expires_at = _ensure_utc(session.expires_at)
    if expires_at and expires_at < now:
        session.is_revoked = True
        session.revoked_at = now
        await db.commit()
        raise TokenExpiredError("Refresh token has expired.")

    # 6. Verify user is active
    user_stmt = select(User).where(User.id == user_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise AppException("User account is inactive or deleted.", status_code=403)

    # 7. Token Rotation: Issue new access token and new refresh token
    new_access_token, access_exp = create_access_token(
        user_id=user.id,
        email=user.email,
        is_owner=user.is_owner,
        device_id=device_id
    )
    new_refresh_token, new_jti, refresh_exp = create_refresh_token(
        user_id=user.id,
        device_id=device_id
    )

    # 8. Mark old session as rotated and record successor JTI
    session.is_revoked = True
    session.revoked_at = now
    session.replaced_by_jti = new_jti

    # 9. Store new session
    new_session = RefreshTokenSession(
        user_id=user.id,
        device_id=device_id,
        jti=new_jti,
        token_hash=hash_token(new_refresh_token),
        expires_at=refresh_exp,
        is_revoked=False,
        user_agent=user_agent,
        ip_address=client_ip,
    )
    db.add(new_session)
    await db.commit()

    expires_in_seconds = int((access_exp - now).total_seconds())
    return new_access_token, new_refresh_token, expires_in_seconds


async def logout_session(
    db: AsyncSession,
    user_id: str,
    refresh_token_str: Optional[str] = None
) -> None:
    """
    Revokes the provided refresh token session, or revokes all sessions for the user if none specified.
    """
    now = datetime.now(timezone.utc)
    if refresh_token_str:
        token_h = hash_token(refresh_token_str)
        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.user_id == user_id,
            RefreshTokenSession.token_hash == token_h
        )
        session = (await db.execute(stmt)).scalar_one_or_none()
        if session:
            session.is_revoked = True
            session.revoked_at = now
            await db.commit()
            logger.info(f"Revoked refresh session {session.jti} for user {user_id}")
    else:
        # Revoke all active sessions for the user
        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.user_id == user_id,
            RefreshTokenSession.is_revoked == False
        )
        sessions = (await db.execute(stmt)).scalars().all()
        for s in sessions:
            s.is_revoked = True
            s.revoked_at = now
        await db.commit()
        logger.info(f"Revoked all {len(sessions)} active sessions for user {user_id}")


async def register_or_update_device(
    db: AsyncSession,
    user_id: str,
    request: DeviceRegisterRequest,
    client_ip: Optional[str] = None
) -> Device:
    """Registers or updates a client device for the authenticated user."""
    stmt = select(Device).where(
        Device.user_id == user_id,
        Device.device_identifier == request.device_identifier
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if device:
        device.device_name = request.device_name
        device.device_type = request.device_type.value
        device.client_version = request.client_version or device.client_version
        device.last_ip_address = client_ip or device.last_ip_address
        device.last_seen_at = now
        device.is_revoked = False
        device.revoked_at = None
    else:
        device = Device(
            user_id=user_id,
            device_identifier=request.device_identifier,
            device_name=request.device_name,
            device_type=request.device_type.value,
            client_version=request.client_version,
            last_ip_address=client_ip,
            last_seen_at=now,
            is_trusted=True,
            is_revoked=False,
        )
        db.add(device)

    await db.commit()
    await db.refresh(device)
    return device


async def list_user_devices(db: AsyncSession, user_id: str) -> List[Device]:
    """Retrieves all registered devices belonging to the user."""
    stmt = select(Device).where(Device.user_id == user_id).order_by(Device.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_user_device(db: AsyncSession, user_id: str, device_id: str) -> Device:
    """
    Revokes authorization for a device and terminates all its active refresh token sessions.
    """
    stmt = select(Device).where(Device.id == device_id, Device.user_id == user_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if not device:
        raise EntityNotFoundError(f"Device with ID '{device_id}' not found.")

    now = datetime.now(timezone.utc)
    device.is_revoked = True
    device.revoked_at = now

    # Revoke all active sessions linked to this device
    sess_stmt = select(RefreshTokenSession).where(
        RefreshTokenSession.device_id == device.id,
        RefreshTokenSession.is_revoked == False
    )
    active_sessions = (await db.execute(sess_stmt)).scalars().all()
    for s in active_sessions:
        s.is_revoked = True
        s.revoked_at = now

    await db.commit()
    await db.refresh(device)
    logger.info(f"Device {device_id} and {len(active_sessions)} linked sessions revoked for user {user_id}")
    return device
