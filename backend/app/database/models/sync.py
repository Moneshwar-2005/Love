"""
Database models for Cross-Device State Synchronization (Phase 09).
Tracks monotonically sequenced change events, device sync cursors, and per-user sync settings.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base
from backend.app.database.models.user import generate_uuid


class SyncEvent(Base):
    """
    Monotonically sequenced state change event log.
    Every persistent state change (conversation, message, approved memory, task, preference)
    appends an immutable record here with an auto-incrementing integer cursor.
    """
    __tablename__ = "sync_events"

    cursor: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Monotonically increasing sequence cursor"
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        default=generate_uuid,
        nullable=False,
        unique=True,
        index=True,
        doc="Globally unique UUID for this sync event"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID who owns this state change"
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Entity category: conversation, message, memory, task, action_approval, preference"
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Canonical ID of the modified entity"
    )
    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type of change: created, updated, deleted"
    )
    origin_device_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        doc="Device ID that originated this change (used for echo suppression)"
    )
    payload_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        doc="JSON serialized entity state or delta"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp of change recording"
    )

    __table_args__ = (
        Index("ix_sync_events_user_cursor", "user_id", "cursor"),
    )

    @property
    def payload(self) -> Dict[str, Any]:
        """Deserialize stored JSON payload."""
        try:
            return json.loads(self.payload_json) if self.payload_json else {}
        except Exception:
            return {}

    def to_change_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching SyncChange schema."""
        return {
            "cursor": self.cursor,
            "event_id": self.event_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "origin_device_id": self.origin_device_id,
            "payload": self.payload,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return f"<SyncEvent(cursor={self.cursor}, entity={self.entity_type}:{self.entity_id}, action={self.action})>"


class UserSyncSettings(Base):
    """
    Per-user synchronization settings and operational mode configuration.
    Defaults to Standalone Mode (sync disabled) for privacy and local-only simplicity.
    """
    __tablename__ = "user_sync_settings"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="User ID"
    )
    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether multi-device synchronization is enabled for this user"
    )
    sync_mode: Mapped[str] = mapped_column(
        String(20),
        default="standalone",
        nullable=False,
        doc="Operational mode: 'standalone' (local only) or 'multi_device'"
    )
    auto_sync_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False,
        doc="Recommended client polling interval in seconds"
    )
    conflict_resolution: Mapped[str] = mapped_column(
        String(30),
        default="last_write_wins",
        nullable=False,
        doc="Conflict resolution policy: 'last_write_wins'"
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of most recent sync operation"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp of settings modification"
    )

    def __repr__(self) -> str:
        return f"<UserSyncSettings(user_id={self.user_id}, mode={self.sync_mode}, enabled={self.sync_enabled})>"


class DeviceSyncCursor(Base):
    """
    Tracks the highest sequence cursor acknowledged by a specific client device.
    Allows measuring sync lag and verifying device catch-up status.
    """
    __tablename__ = "device_sync_cursors"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Record UUID"
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated client device ID"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owning user ID"
    )
    last_acknowledged_cursor: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Highest sequence cursor processed and confirmed by this device"
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of most recent cursor acknowledgement"
    )

    __table_args__ = (
        UniqueConstraint("device_id", "user_id", name="uq_device_sync_cursors_dev_user"),
    )

    def __repr__(self) -> str:
        return f"<DeviceSyncCursor(device_id={self.device_id}, cursor={self.last_acknowledged_cursor})>"
