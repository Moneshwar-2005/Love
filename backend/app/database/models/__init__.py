"""
SQLAlchemy ORM models export package.
All models must be imported here to register properly on Base.metadata.
"""

from backend.app.database.models.conversation import Conversation, Message
from backend.app.database.models.device import Device
from backend.app.database.models.memory import Memory, MemoryAuditLog, MemorySuggestion
from backend.app.database.models.session import RefreshTokenSession
from backend.app.database.models.sync import DeviceSyncCursor, SyncEvent, UserSyncSettings
from backend.app.database.models.task import Task, TaskAction
from backend.app.database.models.user import User, UserCredential

__all__ = [
    "User",
    "UserCredential",
    "Device",
    "RefreshTokenSession",
    "Conversation",
    "Message",
    "Memory",
    "MemoryAuditLog",
    "MemorySuggestion",
    "Task",
    "TaskAction",
    "SyncEvent",
    "UserSyncSettings",
    "DeviceSyncCursor",
]
