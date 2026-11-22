"""
Domain-specific exceptions for Universal Work Intelligence & Tool Orchestration (Phase 05).
"""

from typing import Optional
from backend.app.core.exceptions import AppException


class WorkIntelligenceException(AppException):
    """Base exception for all work intelligence and tool execution domain errors."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        super().__init__(message=message, status_code=status_code, details=details)


class ToolNotFoundError(WorkIntelligenceException):
    """Raised when an requested tool name is not registered in ToolRegistry."""
    def __init__(self, tool_name: str):
        super().__init__(
            message=f"Tool '{tool_name}' was not found in the ToolRegistry.",
            status_code=404,
            details={"tool_name": tool_name}
        )


class ToolExecutionError(WorkIntelligenceException):
    """Raised when tool execution encounters an unhandled runtime error."""
    def __init__(self, tool_name: str, message: str):
        super().__init__(
            message=f"Execution error in tool '{tool_name}': {message}",
            status_code=500,
            details={"tool_name": tool_name}
        )


class ToolPermissionDeniedError(WorkIntelligenceException):
    """Raised when an action violates authorization policy or lacks user approval."""
    def __init__(self, tool_name_or_reason: str, reason: Optional[str] = None):
        if reason is None:
            tool_name = "action"
            actual_reason = tool_name_or_reason
            message = f"Permission denied: {actual_reason}"
        else:
            tool_name = tool_name_or_reason
            actual_reason = reason
            message = f"Permission denied for tool '{tool_name}': {actual_reason}"
        super().__init__(
            message=message,
            status_code=403,
            details={"tool_name": tool_name, "reason": actual_reason}
        )


class ToolTimeoutError(WorkIntelligenceException):
    """Raised when a tool exceeds its configured execution timeout."""
    def __init__(self, tool_name: str, timeout_seconds: int):
        super().__init__(
            message=f"Tool '{tool_name}' exceeded maximum execution duration of {timeout_seconds}s.",
            status_code=504,
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds}
        )


class PathTraversalError(WorkIntelligenceException):
    """Raised when a workspace file tool detects path traversal outside permitted root."""
    def __init__(self, requested_path: str):
        super().__init__(
            message=f"Path traversal blocked: '{requested_path}' resolves outside the permitted workspace directory.",
            status_code=400,
            details={"requested_path": requested_path}
        )


class SensitiveFileAccessError(WorkIntelligenceException):
    """Raised when a workspace tool attempts to access credentials, private keys, or .env files."""
    def __init__(self, filename: str):
        super().__init__(
            message=(
                f"Access to sensitive file '{filename}' is strictly blocked. "
                "LOVE prohibits tools from reading environment files, credentials, private keys, or application databases."
            ),
            status_code=403,
            details={"blocked_file": filename}
        )


class TaskNotFoundError(WorkIntelligenceException):
    """Raised when a requested task ID is missing or unauthorized."""
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task '{task_id}' was not found or access is denied.",
            status_code=404,
            details={"task_id": task_id}
        )


class ActionNotFoundError(WorkIntelligenceException):
    """Raised when a specific task action ID is missing."""
    def __init__(self, action_id: str):
        super().__init__(
            message=f"Task action '{action_id}' was not found.",
            status_code=404,
            details={"action_id": action_id}
        )

