"""
Task and TaskAction database models for Universal Work Intelligence (Phase 05).
Provides persistent tracking of multi-step task plans, tool executions, and approval states.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.database.models.conversation import Conversation
    from backend.app.database.models.user import User


def generate_uuid() -> str:
    """Generate a 36-character hexadecimal UUID string."""
    return str(uuid.uuid4())


class Task(Base, TimestampMixin):
    """
    Persistent high-level work task representing a user objective.
    Coordinates multi-step plans, tool executions, and progress state.
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique task identifier (UUID)"
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user identifier"
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional originating conversation identifier"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Concise title summarizing the task"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Original natural language user request or detailed objective"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        doc="Task status: 'pending', 'planning', 'in_progress', 'awaiting_approval', 'completed', 'failed', 'cancelled'"
    )
    plan_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
        doc="JSON serialized list of planned steps and dependencies"
    )
    result_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Final synthesized summary of completed work and tool outcomes"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Terminal failure or cancellation rationale"
    )
    total_steps: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of structured execution steps"
    )
    completed_steps: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of successfully finalized steps"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when task reached terminal status"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    conversation: Mapped[Optional["Conversation"]] = relationship(foreign_keys=[conversation_id])
    actions: Mapped[List["TaskAction"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAction.step_index"
    )

    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id!r}, status={self.status!r}, user_id={self.user_id!r})>"


class TaskAction(Base, TimestampMixin):
    """
    Individual atomic action or tool invocation within a Task execution plan.
    Enforces risk classifications, approval workflows, and idempotency.
    """
    __tablename__ = "task_actions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        doc="Unique action identifier (UUID)"
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent task identifier"
    )
    step_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Execution order sequence index within the task plan"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Descriptive name of this specific action"
    )
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Unique identifier of the tool to be executed"
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        default="low",
        nullable=False,
        doc="Risk classification: 'low', 'medium', 'high'"
    )
    input_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
        nullable=False,
        doc="JSON serialized validated arguments for tool invocation"
    )
    output_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON serialized structured tool execution output"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
        doc="Action status: 'pending', 'awaiting_approval', 'approved', 'rejected', 'running', 'completed', 'failed', 'skipped'"
    )
    approval_state: Mapped[str] = mapped_column(
        String(20),
        default="not_required",
        nullable=False,
        doc="Approval state: 'not_required', 'pending', 'approved', 'rejected'"
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        doc="User ID who explicitly authorized execution"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when approval or rejection occurred"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Execution error details if invocation failed"
    )
    execution_time_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Runtime latency of tool execution in milliseconds"
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Hash key to prevent duplicate accidental re-execution"
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="actions")

    def __repr__(self) -> str:
        return f"<TaskAction(id={self.id!r}, tool={self.tool_name!r}, status={self.status!r})>"
