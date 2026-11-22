"""
LOVE Universal Work Intelligence & Tool Orchestration Package (Phase 05).
"""

from backend.app.work.exceptions import (
    ActionNotFoundError,
    PathTraversalError,
    SensitiveFileAccessError,
    TaskNotFoundError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionDeniedError,
    ToolTimeoutError,
    WorkIntelligenceException,
)
from backend.app.work.executor import TaskExecutor, get_task_executor
from backend.app.work.permissions import PermissionManager, get_permission_manager
from backend.app.work.planner import TaskPlanner
from backend.app.work.schemas import (
    ActionApprovalRequest,
    ActionStatus,
    ApprovalState,
    PendingApprovalActionResponse,
    PermissionLevel,
    RiskLevel,
    TaskActionResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskStatus,
    TaskStepPlan,
    ToolDefinition,
    ToolResult,
)
from backend.app.work.service import WorkService, get_work_service
from backend.app.work.tools.base import BaseTool
from backend.app.work.tools.calculator import CalculatorTool, SafeMathEvaluator
from backend.app.work.tools.coding_tools import (
    CodeApplyPatchTool,
    CodeInspectStructureTool,
    CodeProposeChangesTool,
    CodeSearchSymbolsTool,
)
from backend.app.work.tools.datetime_tool import DateTimeTool
from backend.app.work.tools.file_tools import (
    WorkspaceCreateFileTool,
    WorkspaceEditFileTool,
    WorkspaceListFilesTool,
    WorkspaceReadFileTool,
    WorkspaceSearchFilesTool,
    get_workspace_root,
    validate_and_resolve_path,
)
from backend.app.work.tools.registry import ToolRegistry, get_tool_registry
from backend.app.work.tools.research_tool import (
    BaseResearchProvider,
    MockResearchProvider,
    ResearchCitation,
    ResearchFinding,
    ResearchSearchTool,
)

__all__ = [
    "WorkIntelligenceException",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolPermissionDeniedError",
    "ToolTimeoutError",
    "PathTraversalError",
    "SensitiveFileAccessError",
    "TaskNotFoundError",
    "ActionNotFoundError",
    "RiskLevel",
    "PermissionLevel",
    "ActionStatus",
    "TaskStatus",
    "ApprovalState",
    "ToolDefinition",
    "ToolResult",
    "TaskStepPlan",
    "TaskCreateRequest",
    "TaskActionResponse",
    "TaskResponse",
    "ActionApprovalRequest",
    "PendingApprovalActionResponse",
    "BaseTool",
    "CalculatorTool",
    "SafeMathEvaluator",
    "DateTimeTool",
    "WorkspaceListFilesTool",
    "WorkspaceReadFileTool",
    "WorkspaceCreateFileTool",
    "WorkspaceEditFileTool",
    "WorkspaceSearchFilesTool",
    "validate_and_resolve_path",
    "get_workspace_root",
    "BaseResearchProvider",
    "MockResearchProvider",
    "ResearchCitation",
    "ResearchFinding",
    "ResearchSearchTool",
    "CodeInspectStructureTool",
    "CodeSearchSymbolsTool",
    "CodeProposeChangesTool",
    "CodeApplyPatchTool",
    "ToolRegistry",
    "get_tool_registry",
    "PermissionManager",
    "get_permission_manager",
    "TaskPlanner",
    "TaskExecutor",
    "get_task_executor",
    "WorkService",
    "get_work_service",
]
