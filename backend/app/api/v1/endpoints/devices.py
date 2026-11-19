"""
Device management API endpoints.
Provides device registration, multi-platform device listing, and remote revocation.
"""

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import get_current_active_user
from backend.app.authentication.service import (
    list_user_devices,
    register_or_update_device,
    revoke_user_device,
)
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from shared.schemas.device import (
    DeviceListResponse,
    DeviceRegisterRequest,
    DeviceResponse,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post(
    "/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or Update Device",
    description="Registers a new hardware or client installation device for the authenticated user, or updates an existing device record."
)
async def register_device_endpoint(
    request: DeviceRegisterRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DeviceResponse:
    """Register or refresh client device record."""
    client_ip = http_request.client.host if http_request.client else None
    device = await register_or_update_device(
        db=db,
        user_id=current_user.id,
        request=request,
        client_ip=client_ip
    )
    return DeviceResponse.model_validate(device)


@router.get(
    "",
    response_model=DeviceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Registered Devices",
    description="Returns all client devices authorized under the authenticated user account."
)
async def list_devices_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DeviceListResponse:
    """List devices associated with the current user."""
    devices = await list_user_devices(db=db, user_id=current_user.id)
    return DeviceListResponse(
        devices=[DeviceResponse.model_validate(d) for d in devices],
        total=len(devices)
    )


@router.delete(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Device",
    description="Revokes device authorization and terminates all active refresh token sessions originating from that device."
)
async def revoke_device_endpoint(
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> DeviceResponse:
    """Revoke authorization for a specific device."""
    device = await revoke_user_device(
        db=db,
        user_id=current_user.id,
        device_id=device_id
    )
    return DeviceResponse.model_validate(device)
