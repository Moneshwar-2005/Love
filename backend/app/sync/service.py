"""
Cross-Device State Synchronization Service for LOVE (Phase 09).
Manages monotonic sequence cursor change events, delta pagination with echo suppression,
cursor acknowledgements, settings management, and client change application.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.database.models.device import Device
from backend.app.database.models.sync import DeviceSyncCursor, SyncEvent, UserSyncSettings
from shared.schemas.sync import (
    SyncAcknowledgeResponse,
    SyncChange,
    SyncChangesResponse,
    SyncPushItem,
    SyncPushResponse,
    SyncSettingsResponse,
    SyncSettingsUpdateRequest,
    SyncStatusResponse,
)

logger = get_logger("sync.service")


class SyncService:
    """
    Central orchestration service for cross-device state synchronization.
    Maintains a durable append-only event stream in SQLite with monotonic integer cursors.
    Supports both Standalone Mode (local only) and Multi-Device Mode (active sync).
    """

    @staticmethod
    def _serialize_payload(payload: Dict[str, Any]) -> str:
        """Serializes payload dictionary to JSON string with datetime fallback."""
        return json.dumps(payload, default=str)

    async def get_or_create_settings(
        self,
        db: AsyncSession,
        user_id: str
    ) -> UserSyncSettings:
        """
        Retrieves user's sync settings. If none exist, initializes default Standalone Mode.
        """
        stmt = select(UserSyncSettings).where(UserSyncSettings.user_id == user_id)
        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSyncSettings(
                user_id=user_id,
                sync_enabled=False,
                sync_mode="standalone",
                auto_sync_interval_seconds=15,
                conflict_resolution="last_write_wins",
            )
            db.add(settings)
            await db.flush()
            logger.info(f"Initialized default standalone sync settings for user {user_id}")

        return settings

    async def record_event(
        self,
        db: AsyncSession,
        user_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        payload: Dict[str, Any],
        origin_device_id: Optional[str] = None
    ) -> SyncEvent:
        """
        Appends an immutable state change event to the user's sync stream.
        Assigns the next sequential integer cursor automatically via SQLite autoincrement.
        """
        payload_json = self._serialize_payload(payload)

        event = SyncEvent(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            origin_device_id=origin_device_id,
            payload_json=payload_json,
        )
        db.add(event)
        await db.flush()

        # Update last synced / modified timestamp on settings if present
        now = datetime.now(timezone.utc)
        await db.execute(
            update(UserSyncSettings)
            .where(UserSyncSettings.user_id == user_id)
            .values(last_synced_at=now, updated_at=now)
        )

        logger.debug(
            f"Recorded sync event [cursor={event.cursor}] user={user_id} "
            f"entity={entity_type}:{entity_id} action={action} origin={origin_device_id}"
        )
        return event

    async def get_sync_status(
        self,
        db: AsyncSession,
        user_id: str,
        device_id: Optional[str] = None
    ) -> SyncStatusResponse:
        """
        Retrieves current synchronization state, highest sequence cursor, and device statistics.
        """
        settings = await self.get_or_create_settings(db, user_id)

        # Get highest cursor
        max_cursor_stmt = select(func.max(SyncEvent.cursor)).where(SyncEvent.user_id == user_id)
        max_cursor_result = await db.execute(max_cursor_stmt)
        current_cursor = max_cursor_result.scalar_one_or_none() or 0

        # Get total event count
        count_stmt = select(func.count(SyncEvent.cursor)).where(SyncEvent.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total_events = count_result.scalar_one_or_none() or 0

        # Get active (non-revoked) authorized devices count
        devices_stmt = select(func.count(Device.id)).where(
            Device.user_id == user_id,
            Device.is_revoked == False
        )
        devices_result = await db.execute(devices_stmt)
        active_devices_count = devices_result.scalar_one_or_none() or 0

        return SyncStatusResponse(
            sync_enabled=settings.sync_enabled,
            sync_mode=settings.sync_mode,
            current_cursor=current_cursor,
            total_events=total_events,
            active_devices_count=active_devices_count,
            last_synced_at=settings.last_synced_at,
            server_time=datetime.now(timezone.utc),
        )

    async def get_changes(
        self,
        db: AsyncSession,
        user_id: str,
        since_cursor: int = 0,
        limit: int = 50,
        exclude_device_id: Optional[str] = None
    ) -> SyncChangesResponse:
        """
        Fetches incremental delta events strictly after since_cursor.
        Applies echo suppression: if exclude_device_id is provided, excludes events
        originating from that device so it does not redundantly process its own writes.
        """
        bounded_limit = min(max(1, limit), 200)

        # Query events with cursor > since_cursor
        query = (
            select(SyncEvent)
            .where(
                SyncEvent.user_id == user_id,
                SyncEvent.cursor > since_cursor
            )
        )

        # Echo suppression: filter out changes originated by this device
        if exclude_device_id:
            query = query.where(
                or_(
                    SyncEvent.origin_device_id != exclude_device_id,
                    SyncEvent.origin_device_id.is_(None)
                )
            )

        query = query.order_by(SyncEvent.cursor.asc()).limit(bounded_limit + 1)
        result = await db.execute(query)
        events = list(result.scalars().all())

        has_more = len(events) > bounded_limit
        batch = events[:bounded_limit]

        # Highest available cursor overall for this user
        max_cursor_stmt = select(func.max(SyncEvent.cursor)).where(SyncEvent.user_id == user_id)
        max_cursor_result = await db.execute(max_cursor_stmt)
        latest_cursor = max_cursor_result.scalar_one_or_none() or 0

        changes = [
            SyncChange(
                cursor=ev.cursor,
                event_id=ev.event_id,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                action=ev.action,
                origin_device_id=ev.origin_device_id,
                payload=ev.payload,
                created_at=ev.created_at,
            )
            for ev in batch
        ]

        return SyncChangesResponse(
            changes=changes,
            since_cursor=since_cursor,
            latest_cursor=latest_cursor,
            has_more=has_more,
            count=len(changes),
        )

    async def acknowledge_cursor(
        self,
        db: AsyncSession,
        user_id: str,
        cursor: int,
        device_id: Optional[str] = None
    ) -> SyncAcknowledgeResponse:
        """
        Records that a client device has successfully fetched and committed events up to cursor.
        Enforces monotonic sequence advancement, bounds validation, and prevents rollback or future acknowledgements.
        """
        if cursor < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cursor cannot be negative."
            )

        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication token must be bound to a registered device."
            )

        # Check latest recorded cursor for this user
        max_cursor_stmt = select(func.max(SyncEvent.cursor)).where(SyncEvent.user_id == user_id)
        max_cursor_res = await db.execute(max_cursor_stmt)
        latest_cursor = max_cursor_res.scalar_one_or_none() or 0

        if cursor > latest_cursor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge future cursor {cursor}; latest recorded event cursor is {latest_cursor}."
            )

        now = datetime.now(timezone.utc)

        # Upsert device sync cursor
        cur_stmt = select(DeviceSyncCursor).where(
            DeviceSyncCursor.device_id == device_id,
            DeviceSyncCursor.user_id == user_id
        )
        cur_result = await db.execute(cur_stmt)
        dev_cursor = cur_result.scalar_one_or_none()

        if dev_cursor:
            if cursor < dev_cursor.last_acknowledged_cursor:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cursor rollback rejected: current acknowledged cursor is {dev_cursor.last_acknowledged_cursor}, cannot roll back to {cursor}."
                )
            dev_cursor.last_acknowledged_cursor = cursor
            dev_cursor.last_synced_at = now
        else:
            dev_cursor = DeviceSyncCursor(
                device_id=device_id,
                user_id=user_id,
                last_acknowledged_cursor=cursor,
                last_synced_at=now
            )
            db.add(dev_cursor)

        # Update Device last_seen_at
        await db.execute(
            update(Device)
            .where(Device.id == device_id, Device.user_id == user_id)
            .values(last_seen_at=now)
        )

        await db.commit()
        return SyncAcknowledgeResponse(
            status="acknowledged",
            cursor=cursor,
            acknowledged_at=now
        )

    async def update_settings(
        self,
        db: AsyncSession,
        user_id: str,
        update_req: SyncSettingsUpdateRequest,
        origin_device_id: Optional[str] = None
    ) -> UserSyncSettings:
        """
        Updates synchronization settings (e.g. toggling Standalone vs Multi-Device mode).
        Broadcasts a 'preference' sync event so connected clients adjust behavior.
        """
        settings = await self.get_or_create_settings(db, user_id)

        if update_req.sync_enabled is not None:
            settings.sync_enabled = update_req.sync_enabled
            if update_req.sync_enabled and update_req.sync_mode is None:
                settings.sync_mode = "multi_device"
            elif not update_req.sync_enabled and update_req.sync_mode is None:
                settings.sync_mode = "standalone"

        if update_req.sync_mode is not None:
            settings.sync_mode = update_req.sync_mode
            if update_req.sync_mode == "multi_device":
                settings.sync_enabled = True
            elif update_req.sync_mode == "standalone":
                settings.sync_enabled = False

        if update_req.auto_sync_interval_seconds is not None:
            settings.auto_sync_interval_seconds = update_req.auto_sync_interval_seconds

        settings.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Emit sync preference change event
        await self.record_event(
            db=db,
            user_id=user_id,
            entity_type="preference",
            entity_id="sync_settings",
            action="updated",
            payload={
                "sync_enabled": settings.sync_enabled,
                "sync_mode": settings.sync_mode,
                "auto_sync_interval_seconds": settings.auto_sync_interval_seconds,
                "conflict_resolution": settings.conflict_resolution,
            },
            origin_device_id=origin_device_id
        )

        await db.commit()
        await db.refresh(settings)
        return settings

    ALLOWED_PUSH_ENTITY_TYPES = {"preference"}
    ALLOWED_PREFERENCE_KEYS = {
        "mobile_haptic_feedback",
        "theme",
        "notifications_enabled",
        "sound_volume",
        "audio_preferences",
        "client_preferences",
        "ui_preferences"
    }
    FORBIDDEN_PAYLOAD_KEYS = {
        "cursor", "event_id", "user_id", "created_at",
        "origin_device_id", "is_owner", "is_revoked", "role", "password", "token"
    }
    ALLOWED_PUSH_ACTIONS = {"created", "updated"}

    async def apply_pushed_changes(
        self,
        db: AsyncSession,
        user_id: str,
        origin_device_id: Optional[str],
        items: List[SyncPushItem]
    ) -> SyncPushResponse:
        """
        Applies client-originated state changes with strict entity and field allowlisting.
        Guarantees that clients cannot forge work approvals, tasks, memories, or messages.
        Implements Last-Write-Wins and records server sync events.
        """
        if not origin_device_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Push operations require an authenticated registered device session."
            )

        accepted = 0
        conflicts = 0

        for item in items:
            # 1. Entity type allowlist enforcement
            if item.entity_type not in self.ALLOWED_PUSH_ENTITY_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Entity type '{item.entity_type}' is not client-pushable. "
                        f"Approvals, tasks, memories, and messages must use their dedicated authenticated APIs."
                    )
                )

            # 2. Preference key allowlist enforcement
            if item.entity_id not in self.ALLOWED_PREFERENCE_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Preference key '{item.entity_id}' is not in the client-pushable allowlist."
                )

            # 3. Action allowlist enforcement
            if item.action not in self.ALLOWED_PUSH_ACTIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Action '{item.action}' is not permitted for client synchronization push."
                )

            # 4. Forbidden server-authoritative payload keys enforcement
            if not isinstance(item.payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Push payload must be a valid JSON dictionary."
                )

            for forbidden_key in self.FORBIDDEN_PAYLOAD_KEYS:
                if forbidden_key in item.payload:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Payload contains forbidden server-authoritative field '{forbidden_key}'."
                    )

            # Last-Write-Wins: record incoming state as newest canonical change
            await self.record_event(
                db=db,
                user_id=user_id,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                action=item.action,
                payload=item.payload,
                origin_device_id=origin_device_id,
            )
            accepted += 1

        await db.commit()

        # Get the new highest cursor
        max_cursor_stmt = select(func.max(SyncEvent.cursor)).where(SyncEvent.user_id == user_id)
        max_cursor_res = await db.execute(max_cursor_stmt)
        new_cursor = max_cursor_res.scalar_one_or_none() or 0

        return SyncPushResponse(
            accepted=accepted,
            conflicts=conflicts,
            new_cursor=new_cursor
        )


_sync_service_instance: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    """Dependency provider for singleton SyncService instance."""
    global _sync_service_instance
    if _sync_service_instance is None:
        _sync_service_instance = SyncService()
    return _sync_service_instance
