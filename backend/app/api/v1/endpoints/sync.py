"""
Cross-Device State Synchronization Endpoints (Phase 09).
Provides delta change retrieval, sequence cursor acknowledgement, sync status,
settings configuration, and client change pushing.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import (
    get_current_active_user,
    get_current_device_id,
)
from backend.app.database.models.device import Device
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.sync.service import SyncService, get_sync_service
from shared.schemas.sync import (
    SyncAcknowledgeRequest,
    SyncAcknowledgeResponse,
    SyncChangesResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncSettingsResponse,
    SyncSettingsUpdateRequest,
    SyncStatusResponse,
)

router = APIRouter(prefix="/sync", tags=["Cross-Device Synchronization"])


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Synchronization Status",
    description="Returns current sync state, mode (standalone vs multi-device), latest cursor, and active devices count."
)
async def get_sync_status(
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncStatusResponse:
    """Retrieve synchronization health, cursor position, and device statistics."""
    return await sync_service.get_sync_status(
        db=db,
        user_id=current_user.id,
        device_id=device_id
    )


@router.get(
    "/changes",
    response_model=SyncChangesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Incremental Sync Changes",
    description="Fetches state changes since a specified cursor. Optionally applies echo suppression if exclude_device_id is provided."
)
async def get_sync_changes(
    since_cursor: int = Query(default=0, ge=0, description="Resume sequence cursor"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum changes to return"),
    exclude_device_id: Optional[str] = Query(default=None, description="Device ID to exclude from changes (echo suppression)"),
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncChangesResponse:
    """Fetch delta changes strictly after since_cursor with optional echo suppression."""
    if exclude_device_id and exclude_device_id != device_id:
        dev_stmt = select(Device).where(Device.id == exclude_device_id, Device.user_id == current_user.id)
        dev_res = await db.execute(dev_stmt)
        if not dev_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot exclude an unauthorized or foreign device ID."
            )
    return await sync_service.get_changes(
        db=db,
        user_id=current_user.id,
        since_cursor=since_cursor,
        limit=limit,
        exclude_device_id=exclude_device_id
    )


@router.post(
    "/acknowledge",
    response_model=SyncAcknowledgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge Processed Cursor",
    description="Confirms that the client device has successfully applied changes up to the given cursor."
)
async def acknowledge_cursor(
    request: SyncAcknowledgeRequest,
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncAcknowledgeResponse:
    """Acknowledge processed sequence cursor for client device."""
    if request.device_id and request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device ID mismatch: cannot acknowledge cursor on behalf of another device."
        )
    effective_device = device_id
    if not effective_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication token must be bound to a registered device."
        )
    return await sync_service.acknowledge_cursor(
        db=db,
        user_id=current_user.id,
        cursor=request.cursor,
        device_id=effective_device
    )


@router.get(
    "/settings",
    response_model=SyncSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Synchronization Settings",
    description="Retrieves the user's sync preferences (standalone vs multi-device, auto-sync interval)."
)
async def get_sync_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncSettingsResponse:
    """Fetch current synchronization settings for the authenticated user."""
    settings = await sync_service.get_or_create_settings(db=db, user_id=current_user.id)
    return SyncSettingsResponse.model_validate(settings)


@router.put(
    "/settings",
    response_model=SyncSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Synchronization Settings",
    description="Configures synchronization preferences: toggle between standalone and multi-device modes."
)
async def update_sync_settings(
    request: SyncSettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncSettingsResponse:
    """Update user synchronization mode and options."""
    settings = await sync_service.update_settings(
        db=db,
        user_id=current_user.id,
        update_req=request,
        origin_device_id=device_id
    )
    return SyncSettingsResponse.model_validate(settings)


@router.post(
    "/push",
    response_model=SyncPushResponse,
    status_code=status.HTTP_200_OK,
    summary="Push Client State Changes",
    description="Applies client-originated state changes using Last-Write-Wins conflict resolution."
)
async def push_sync_changes(
    request: SyncPushRequest,
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncPushResponse:
    """Submit local client state changes to be merged and sequenced by server."""
    return await sync_service.apply_pushed_changes(
        db=db,
        user_id=current_user.id,
        origin_device_id=device_id,
        items=request.changes
    )
