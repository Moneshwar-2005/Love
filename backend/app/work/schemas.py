"""
Pydantic Schemas and Enums for Universal Work Intelligence & Tool Orchestration (Phase 05).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(str, Enum):
    """Action and Tool risk classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PermissionLevel(str, Enum):
    """Authorization policy governing tool execution."""
    AUTO_PERMIT = "auto_permit"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_EXPLICIT_APPROVAL = "requires_explicit_approval"


class ActionStatus(str, Enum):
    """Lifecycle status of an individual task action."""
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """High-level status of a multi-step task."""
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalState(str, Enum):
    """Explicit human-in-the-loop authorization state."""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ToolDefinition(BaseModel):
    """Metadata catalog schema describing an available tool."""
    name: str = Field(..., description="Unique machine-readable tool name")
    description: str = Field(..., description="Description of tool capability and use cases")
    category: str = Field(default="general", description="Tool category (e.g. math, file, coding, system)")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema defining parameters")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema defining output structure")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Operational risk tier")
    permission_level: PermissionLevel = Field(default=PermissionLevel.AUTO_PERMIT, description="Required permission")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Maximum execution duration before timeout")
    is_available: bool = Field(default=True, description="Whether tool runtime dependencies are satisfied")


class ToolResult(BaseModel):
    """Standardized response from tool invocation."""
    tool_name: str
    success: bool = True
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def remap_success(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapped = dict(data)
            if "is_success" in mapped and "success" not in mapped:
                mapped["success"] = mapped["is_success"]
            return mapped
        return data

    @property
    def is_success(self) -> bool:
        return self.success


class TaskStepPlan(BaseModel):
    """Structured plan element for an individual step."""
    step_index: int = Field(default=1)
    title: str = Field(default="")
    tool_name: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[int] = Field(default_factory=list, description="Step indices that must succeed before this step")
    risk_level: RiskLevel = RiskLevel.LOW
    is_parallelizable: bool = False

    @model_validator(mode="before")
    @classmethod
    def remap_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapped = dict(data)
            if "step_number" in mapped and "step_index" not in mapped:
                mapped["step_index"] = mapped["step_number"]
            if "description" in mapped and "title" not in mapped:
                mapped["title"] = mapped["description"]
            if "arguments" in mapped and "input_args" not in mapped:
                mapped["input_args"] = mapped["arguments"]
            if "dependencies" in mapped and "depends_on" not in mapped:
                mapped["depends_on"] = mapped["dependencies"]
            return mapped
        return data

    @property
    def step_number(self) -> int:
        return self.step_index

    @property
    def description(self) -> str:
        return self.title

    @property
    def arguments(self) -> Dict[str, Any]:
        return self.input_args

    @property
    def dependencies(self) -> List[int]:
        return self.depends_on


class TaskCreateRequest(BaseModel):
    """Request payload to initiate a new work task."""
    description: str = Field(..., min_length=3, description="Natural language description of objective")
    title: Optional[str] = Field(default=None, max_length=255, description="Optional brief title")
    conversation_id: Optional[str] = Field(default=None, description="Optional associated conversation UUID")
    context_overrides: Dict[str, Any] = Field(default_factory=dict, description="Optional custom parameters")


class TaskActionResponse(BaseModel):
    """Serialized representation of a planned or executed action."""
    id: str
    task_id: str
    step_index: int
    title: str
    tool_name: str
    risk_level: RiskLevel
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    status: ActionStatus
    approval_state: ApprovalState
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    """Serialized representation of a complete work task."""
    id: str
    user_id: str
    conversation_id: Optional[str] = None
    title: str
    description: str
    status: TaskStatus
    plan: List[TaskStepPlan] = Field(default_factory=list)
    actions: List[TaskActionResponse] = Field(default_factory=list)
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    total_steps: int
    completed_steps: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionApprovalRequest(BaseModel):
    """Request payload to approve or reject a pending action."""
    approved: bool = Field(..., description="True to authorize execution; False to reject")
    reason: Optional[str] = Field(default=None, description="Optional user commentary or rationale")


class PendingApprovalActionResponse(BaseModel):
    """Compound model representing an action awaiting human approval."""
    task_id: str
    task_title: str
    action: TaskActionResponse

