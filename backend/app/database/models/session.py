"""
Refresh token session database model.
Tracks active, rotated, and revoked token sessions for multi-device authorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base
from backend.app.database.models.user import generate_uuid

if TYPE_CHECKING:
    from backend.app.database.models.device import Device
    from backend.app.database.models.user import User


class RefreshTokenSession(Base):
    """
    Stores refresh token metadata and rotation state.
    Plaintext tokens are never stored; only cryptographic SHA-256 hashes and JTIs.
    """
    __tablename__ = "refresh_token_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique session identifier"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated user ID"
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Associated device ID (if registered)"
    )
    jti: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        doc="JWT Token ID claim (unique per token issuance)"
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        doc="Cryptographic SHA-256 hash of the complete refresh token"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Token expiration timestamp"
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this token session has been revoked or rotated"
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the token was rotated or revoked"
    )
    replaced_by_jti: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="JTI of the replacement token issued during rotation (detects reuse attacks)"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Client User-Agent header string"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address of client when token was created"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Session creation timestamp"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    device: Mapped[Optional["Device"]] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<RefreshTokenSession(id={self.id!r}, user_id={self.user_id!r}, revoked={self.is_revoked!r})>"
