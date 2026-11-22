"""
Persistent Personal Memory and Audit Log database models (Phase 04).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.database.models.user import User


def generate_uuid() -> str:
    """Generate a 36-character hexadecimal UUID string."""
    return str(uuid.uuid4())


class Memory(Base, TimestampMixin):
    """
    Canonical personal memory record belonging to an authenticated user.
    Stores durable facts, preferences, project patterns, and knowledge.
    """
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique memory record identifier (UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user identifier"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Memory category: 'personal', 'project', 'conversational', 'knowledge'"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Canonical text statement of the memory"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional concise one-line summary"
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        default="explicit_user",
        nullable=False,
        doc="Origin category: 'explicit_user', 'conversation_extraction', 'system_rule', 'reference_doc'"
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Referenced source entity ID (e.g. conversation_id)"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        doc="Reliability / confidence score (0.0 to 1.0)"
    )
    importance: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Priority weighting tier from 1 (minor) to 5 (critical)"
    )
    tags_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default="[]",
        nullable=False,
        doc="JSON list of associated search tags"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default="{}",
        nullable=False,
        doc="Structured metadata (project name, entities, timestamps)"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether the memory is archived"
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Counter tracking retrieval frequency"
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Timestamp of most recent retrieval"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="memories")

    __table_args__ = (
        Index("ix_memories_user_archived", "user_id", "is_archived"),
    )

    def __repr__(self) -> str:
        return f"<Memory(id={self.id!r}, category={self.category!r}, user_id={self.user_id!r})>"


class MemoryAuditLog(Base):
    """
    Auditable log of memory lifecycle events (creation, update, access, deletion).
    Enables owners to inspect and verify what LOVE remembers and when it was modified.
    """
    __tablename__ = "memory_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    memory_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Action: 'created', 'updated', 'deleted', 'retrieved', 'archived', 'restored', 'reindexed'"
    )
    details_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Non-sensitive structured event summary"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="memory_audits")

    def __repr__(self) -> str:
        return f"<MemoryAuditLog(id={self.id!r}, action={self.action!r}, user_id={self.user_id!r})>"


class MemorySuggestion(Base, TimestampMixin):
    """
    Pending memory suggestion extracted from conversation turns.
    Requires explicit user approval before being promoted to a canonical permanent memory.
    Ensures that auto-extracted information is never saved without user consent.
    """
    __tablename__ = "memory_suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique suggestion identifier (UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target user identifier"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Suggested memory category: 'personal', 'project', 'conversational', 'knowledge'"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Candidate memory text"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Concise candidate summary"
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Rationale for why LOVE suggests remembering this fact"
    )
    source_statement: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Original prompt sentence that triggered the extraction"
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Originating conversation or message ID"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.8,
        nullable=False,
        doc="Extraction confidence score"
    )
    importance: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Suggested importance weighting (1-5)"
    )
    tags_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default="[]",
        nullable=False,
        doc="JSON list of associated search tags"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default="{}",
        nullable=False,
        doc="Structured metadata"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        doc="Suggestion status: 'pending', 'approved', 'rejected'"
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="memory_suggestions")

    def __repr__(self) -> str:
        return f"<MemorySuggestion(id={self.id!r}, status={self.status!r}, user_id={self.user_id!r})>"
