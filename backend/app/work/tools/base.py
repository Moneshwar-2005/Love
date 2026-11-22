"""
Abstract Base Tool Interface for Universal Work Intelligence (Phase 05).
"""

from abc import ABC, abstractmethod
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel

from backend.app.work.schemas import PermissionLevel, RiskLevel, ToolDefinition, ToolResult


class BaseTool(ABC):
    """
    Standard interface for all LOVE tools.
    Decouples tool definition and execution from conversational and routing engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique machine-readable tool identifier (e.g. 'calculator', 'workspace_read_file')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear description of capability, input parameters, and purpose."""
        pass

    @property
    def category(self) -> str:
        """Tool domain category (math, datetime, file, code, research, system)."""
        return "general"

    @property
    def risk_level(self) -> RiskLevel:
        """Operational risk level: low (read-only), medium (workspace modifications), high (destructive)."""
        return RiskLevel.LOW

    @property
    def permission_level(self) -> PermissionLevel:
        """Execution policy: auto_permit, requires_confirmation, requires_explicit_approval."""
        if self.risk_level == RiskLevel.HIGH:
            return PermissionLevel.REQUIRES_EXPLICIT_APPROVAL
        elif self.risk_level == RiskLevel.MEDIUM:
            return PermissionLevel.REQUIRES_CONFIRMATION
        return PermissionLevel.AUTO_PERMIT

    @property
    def timeout_seconds(self) -> int:
        """Maximum allowable execution duration before cancellation."""
        return 30

    @property
    def is_available(self) -> bool:
        """Verifies whether tool runtime prerequisites and dependencies are satisfied."""
        return True

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema defining validated arguments for execution."""
        pass

    @property
    def output_schema(self) -> Dict[str, Any]:
        """JSON Schema defining structured output format."""
        return {"type": "object"}

    @property
    def definition(self) -> ToolDefinition:
        """Returns metadata definition schema for discovery."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            risk_level=self.risk_level,
            permission_level=self.permission_level,
            timeout_seconds=self.timeout_seconds,
            is_available=self.is_available,
        )

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Internal asynchronous tool execution logic. To be implemented by subclasses."""
        pass

    async def execute(self, **kwargs) -> ToolResult:
        """
        Public execution wrapper measuring runtime latency and capturing unhandled errors.
        """
        start = time.perf_counter()
        try:
            output = await self.run(**kwargs)
            duration_ms = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=output,
                execution_time_ms=round(duration_ms, 2),
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
                execution_time_ms=round(duration_ms, 2),
            )
