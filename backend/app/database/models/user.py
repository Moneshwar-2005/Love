"""
User and UserCredential database models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.database.models.device import Device
    from backend.app.database.models.session import RefreshTokenSession


def generate_uuid() -> str:
    """Generate a 36-character hexadecimal UUID string."""
    return str(uuid.uuid4())


class User(Base, TimestampMixin):
    """
    Core User entity for the LOVE assistant ecosystem.
    Represents the assistant owner or an authorized user.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique user identifier (UUID)"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="User primary email address"
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique username handle"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Display name or real full name"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the user account has verified identity"
    )
    is_owner: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the user is the primary assistant owner with administrative control"
    )

    # Relationships
    credential: Mapped[Optional["UserCredential"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    devices: Mapped[List["Device"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Device.created_at)"
    )
    sessions: Mapped[List["RefreshTokenSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(RefreshTokenSession.created_at)"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, email={self.email!r}, is_owner={self.is_owner!r})>"


class UserCredential(Base):
    """
    Stores sensitive authentication credentials separately from user profile data.
    """
    __tablename__ = "user_credentials"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Argon2id password hash string"
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Counter for consecutive failed login attempts"
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Account lockout timestamp for brute force defense"
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last successful authentication"
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the password was last modified"
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="credential")

    def __repr__(self) -> str:
        return f"<UserCredential(user_id={self.user_id!r}, failed_attempts={self.failed_login_attempts!r})>"
