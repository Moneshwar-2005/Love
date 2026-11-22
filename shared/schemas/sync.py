"""
Pydantic schemas for Cross-Device State Synchronization (Phase 09).
Provides request/response schemas for sync status, incremental changes, cursor acknowledgements,
settings, and client change pushing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SyncChange(BaseModel):
    """A discrete state change event in the monotonic sequence."""
    cursor: int = Field(..., description="Monotonically increasing sequence cursor")
    event_id: str = Field(..., description="Globally unique UUID for this sync event")
    entity_type: str = Field(..., description="Entity category: conversation, message, memory, task, action_approval, preference")
    entity_id: str = Field(..., description="Canonical ID of the modified entity")
    action: str = Field(..., description="Type of operation: created, updated, deleted")
    origin_device_id: Optional[str] = Field(None, description="UUID of device that produced this change, if any")
    payload: Dict[str, Any] = Field(default_factory=dict, description="State payload of the entity")
    created_at: datetime = Field(..., description="Timestamp when event was recorded")

    model_config = ConfigDict(from_attributes=True)


class SyncChangesResponse(BaseModel):
    """Paginated collection of sync events since a specified cursor."""
    changes: List[SyncChange] = Field(..., description="List of incremental change events")
    since_cursor: int = Field(..., description="The cursor offset supplied by the client")
    latest_cursor: int = Field(..., description="The highest cursor currently available on server")
    has_more: bool = Field(..., description="True if additional changes exceed pagination limit")
    count: int = Field(..., description="Number of change records returned in this batch")


class SyncStatusResponse(BaseModel):
    """High-level synchronization health and sequence progress."""
    sync_enabled: bool = Field(..., description="Whether multi-device synchronization is enabled")
    sync_mode: str = Field(..., description="'standalone' (local SQLite only) or 'multi_device'")
    current_cursor: int = Field(..., description="Highest sequence cursor recorded for the user")
    total_events: int = Field(..., description="Total cumulative sync events in log")
    active_devices_count: int = Field(..., description="Number of authorized, non-revoked devices")
    last_synced_at: Optional[datetime] = Field(None, description="Timestamp of most recent sync activity")
    server_time: datetime = Field(..., description="Current UTC timestamp of the server")


class SyncAcknowledgeRequest(BaseModel):
    """Payload to confirm successful client processing of changes up to a cursor."""
    cursor: int = Field(..., ge=0, description="Highest processed sequence cursor")
    device_id: Optional[str] = Field(None, description="Client device identifier")


class SyncAcknowledgeResponse(BaseModel):
    """Confirmation of acknowledged cursor."""
    status: str = Field(default="acknowledged", description="Status confirmation")
    cursor: int = Field(..., description="The cursor acknowledged")
    acknowledged_at: datetime = Field(..., description="Server timestamp of acknowledgement")


class SyncSettingsResponse(BaseModel):
    """Synchronization preferences for the authenticated user."""
    sync_enabled: bool = Field(..., description="Whether sync is active")
    sync_mode: str = Field(..., description="'standalone' or 'multi_device'")
    auto_sync_interval_seconds: int = Field(..., description="Background poll interval in seconds")
    conflict_resolution: str = Field(..., description="Strategy: last_write_wins")
    updated_at: datetime = Field(..., description="Timestamp when settings were last modified")

    model_config = ConfigDict(from_attributes=True)


class SyncSettingsUpdateRequest(BaseModel):
    """Payload to modify synchronization preferences."""
    sync_enabled: Optional[bool] = Field(None, description="Enable or disable sync")
    sync_mode: Optional[str] = Field(None, description="'standalone' or 'multi_device'")
    auto_sync_interval_seconds: Optional[int] = Field(None, ge=3, le=3600, description="Poll interval seconds")


class SyncPushItem(BaseModel):
    """An individual entity change submitted by a client."""
    entity_type: str = Field(..., description="Entity category: conversation, message, memory, task, preference")
    entity_id: str = Field(..., description="Canonical entity ID")
    action: str = Field(..., description="created, updated, deleted")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes")
    client_timestamp: Optional[datetime] = Field(None, description="Client-side UTC timestamp")


class SyncPushRequest(BaseModel):
    """Batch of client-originated state changes to apply."""
    changes: List[SyncPushItem] = Field(..., min_length=1, description="List of local changes")


class SyncPushResponse(BaseModel):
    """Result of processing pushed client changes."""
    accepted: int = Field(..., description="Number of successfully applied changes")
    conflicts: int = Field(..., description="Number of changes resolved via conflict strategy")
    new_cursor: int = Field(..., description="New highest sequence cursor on server")
