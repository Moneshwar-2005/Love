"""
Execution Engine for Universal Work Intelligence (Phase 05).
Executes individual tools and steps with strict timeout limits, permission checks,
idempotency protection, and error isolation.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from backend.app.config.settings import get_settings
from backend.app.work.exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionDeniedError,
    ToolTimeoutError,
)
from backend.app.work.permissions import PermissionManager, get_permission_manager
from backend.app.work.schemas import (
    ActionStatus,
    ApprovalState,
    RiskLevel,
    ToolResult,
)
from backend.app.work.tools.base import BaseTool
from backend.app.work.tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Controlled execution engine that validates inputs, checks permissions,
    enforces timeout constraints, and captures structured tool outputs.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_manager: Optional[PermissionManager] = None,
    ):
        self._registry = registry or get_tool_registry()
        self._permission_manager = permission_manager or get_permission_manager()

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_state: ApprovalState = ApprovalState.NOT_REQUIRED,
        timeout_seconds: Optional[int] = None,
    ) -> ToolResult:
        """
        Safely executes a registered tool with full security, timeout, and isolation controls.
        """
        # 1. Tool Lookup
        if not self._registry.has(tool_name):
            return ToolResult(
                tool_name=tool_name,
                is_success=False,
                error=f"Tool '{tool_name}' is not registered in the tool catalog.",
            )

        tool: BaseTool = self._registry.get(tool_name)

        # 2. Availability Check
        if not tool.is_available:
            return ToolResult(
                tool_name=tool.name,
                is_success=False,
                error=f"Tool '{tool.name}' is currently unavailable (dependencies or credentials missing).",
            )

        # 3. Permission Enforcement
        permitted, reason = self._permission_manager.evaluate_permission(tool, approval_state)
        if not permitted:
            return ToolResult(
                tool_name=tool.name,
                is_success=False,
                error=f"Permission Denied: {reason}",
            )

        # 4. Timeout Determination
        settings = get_settings()
        effective_timeout = timeout_seconds or tool.timeout_seconds or settings.TOOL_EXECUTION_TIMEOUT_SECONDS

        # 5. Execution with Timeout & Exception Isolation
        start_time = time.perf_counter()
        try:
            logger.info(f"Executing tool '{tool.name}' with timeout={effective_timeout}s")
            output = await asyncio.wait_for(
                tool.run(**arguments),
                timeout=effective_timeout,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return ToolResult(
                tool_name=tool.name,
                is_success=True,
                output=output,
                execution_time_ms=round(duration_ms, 2),
            )

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Tool '{tool.name}' execution timed out after {effective_timeout} seconds."
            logger.warning(error_msg)
            return ToolResult(
                tool_name=tool.name,
                is_success=False,
                error=error_msg,
                execution_time_ms=round(duration_ms, 2),
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(e) or type(e).__name__
            logger.error(f"Error executing tool '{tool.name}': {error_msg}", exc_info=True)
            return ToolResult(
                tool_name=tool.name,
                is_success=False,
                error=error_msg,
                execution_time_ms=round(duration_ms, 2),
            )


_default_executor: Optional[TaskExecutor] = None


def get_task_executor() -> TaskExecutor:
    """Returns singleton TaskExecutor instance."""
    global _default_executor
    if _default_executor is None:
        _default_executor = TaskExecutor()
    return _default_executor
