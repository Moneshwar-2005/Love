"""
Conversation and Message database models for the Universal Intelligence Layer (Phase 03).
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


class Conversation(Base, TimestampMixin):
    """
    Represents an ongoing multi-turn dialogue thread between a user and LOVE.
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique conversation identifier (UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user identifier"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation",
        doc="Human-readable title or generated conversation topic"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional condensed synopsis of the conversation"
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the conversation is pinned in the client interface"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the conversation is archived"
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Timestamp of the most recent message in this conversation"
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Non-sensitive JSON-serialized session or routing metadata"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id!r}, title={self.title!r}, user_id={self.user_id!r})>"


class Message(Base, TimestampMixin):
    """
    Individual turn within a conversation (user query, assistant reply, system prompt, or tool result).
    """
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique message identifier (UUID)"
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent conversation identifier"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Originating or responding user identifier"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Message author role: 'user', 'assistant', 'system', 'tool'"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full text content of the message"
    )
    intent: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Classified user task intent (e.g. coding, debugging, general, reasoning, creative)"
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="AI provider identifier that generated this response (e.g. 'ollama', 'openai', 'anthropic')"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Specific model identifier that generated this response (e.g. 'llama3.2:3b', 'gpt-4o')"
    )
    tokens_prompt: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Prompt token count"
    )
    tokens_completion: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Completion token count"
    )
    tokens_total: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Total tokens consumed"
    )
    latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Inference turnaround latency in milliseconds"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
        doc="Generation status: 'completed', 'streaming', 'interrupted', 'failed'"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if generation failed or was interrupted"
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id!r}, role={self.role!r}, status={self.status!r})>"
