"""
Tool Registry for Universal Work Intelligence (Phase 05).
Manages tool discovery, metadata catalogs, risk profiles, and runtime resolution.
"""

from typing import Dict, List, Optional
from backend.app.work.exceptions import ToolNotFoundError
from backend.app.work.schemas import RiskLevel, ToolDefinition
from backend.app.work.tools.base import BaseTool
from backend.app.work.tools.calculator import CalculatorTool
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
)
from backend.app.work.tools.research_tool import ResearchSearchTool


class ToolRegistry:
    """
    Central repository for discovering, querying, and executing registered tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Initializes all built-in safe Phase 05 tools."""
        defaults: List[BaseTool] = [
            CalculatorTool(),
            DateTimeTool(),
            WorkspaceListFilesTool(),
            WorkspaceReadFileTool(),
            WorkspaceCreateFileTool(),
            WorkspaceEditFileTool(),
            WorkspaceSearchFilesTool(),
            ResearchSearchTool(),
            CodeInspectStructureTool(),
            CodeSearchSymbolsTool(),
            CodeProposeChangesTool(),
            CodeApplyPatchTool(),
        ]
        for tool in defaults:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Registers a tool in the registry."""
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> bool:
        """Removes a tool from the registry."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False

    def get(self, tool_name: str) -> BaseTool:
        """Retrieves a registered tool by its unique name, or raises ToolNotFoundError."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not registered.")
        return tool

    def has(self, tool_name: str) -> bool:
        """Checks if a tool name is registered."""
        return tool_name in self._tools

    def list_tools(
        self,
        category: Optional[str] = None,
        max_risk: Optional[RiskLevel] = None,
        available_only: bool = True,
    ) -> List[ToolDefinition]:
        """
        Returns a list of metadata definitions for registered tools,
        with optional filtering by category, risk ceiling, and availability.
        """
        risk_order = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}
        definitions: List[ToolDefinition] = []

        for tool in self._tools.values():
            if available_only and not tool.is_available:
                continue
            if category and tool.category.lower() != category.lower():
                continue
            if max_risk:
                if risk_order.get(tool.risk_level, 99) > risk_order.get(max_risk, 99):
                    continue
            definitions.append(tool.definition)

        return sorted(definitions, key=lambda d: d.name)


_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Returns the process-wide singleton ToolRegistry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
