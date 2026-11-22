"""
Task Planning Engine for Universal Work Intelligence (Phase 05).
Deconstructs complex user requests into structured, dependency-aware execution steps.
Provider-independent: operates deterministically and handles tool identification safely.
"""

import re
from typing import Any, Dict, List, Optional
from backend.app.intelligence.schemas import IntentResult, TaskIntent
from backend.app.work.schemas import RiskLevel, TaskStepPlan
from backend.app.work.tools.registry import ToolRegistry, get_tool_registry


class TaskPlanner:
    """
    Analyzes user intent and goals to generate structured step-by-step task plans.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self._registry = registry or get_tool_registry()

    def plan_task(
        self,
        goal: str,
        intent_result: Optional[IntentResult] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[TaskStepPlan]:
        """
        Decomposes a user prompt into structured executable steps.
        """
        text = goal.strip()
        lower = text.lower()
        steps: List[TaskStepPlan] = []

        # 1. Multi-step project creation & inspection
        if re.search(r"create\s+.*(?:folder|project).*(?:readme|file).*(?:python|example).*(?:inspect|read)", lower, re.DOTALL):
            folder_match = re.search(r"(?:folder|directory|project)\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-]+)", lower)
            folder_prefix = f"{folder_match.group(1)}/" if folder_match else "test_project/"
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Create README file in '{folder_prefix}'",
                    tool_name="workspace_create_file",
                    arguments={
                        "path": f"{folder_prefix}README.md",
                        "content": "# Test Project\nCreated by LOVE Assistant.\n",
                        "overwrite": True
                    },
                    risk_level=RiskLevel.MEDIUM,
                    dependencies=[]
                )
            )
            steps.append(
                TaskStepPlan(
                    step_number=2,
                    description=f"Create Python example file in '{folder_prefix}'",
                    tool_name="workspace_create_file",
                    arguments={
                        "path": f"{folder_prefix}example.py",
                        "content": "# Example Python Script\ndef run():\n    print('LOVE work execution verified')\n\nif __name__ == '__main__':\n    run()\n",
                        "overwrite": True
                    },
                    risk_level=RiskLevel.MEDIUM,
                    dependencies=[]
                )
            )
            steps.append(
                TaskStepPlan(
                    step_number=3,
                    description=f"Inspect README file in '{folder_prefix}'",
                    tool_name="workspace_read_file",
                    arguments={"path": f"{folder_prefix}README.md"},
                    risk_level=RiskLevel.LOW,
                    dependencies=[1]
                )
            )
            steps.append(
                TaskStepPlan(
                    step_number=4,
                    description=f"Inspect Python file in '{folder_prefix}'",
                    tool_name="workspace_read_file",
                    arguments={"path": f"{folder_prefix}example.py"},
                    risk_level=RiskLevel.LOW,
                    dependencies=[2]
                )
            )
            return steps

        # 2. DateTime tasks
        if re.search(r"\b(?:days\s+between|number\s+of\s+days|difference\s+between\s+(?:two\s+)?dates|how\s+many\s+days\s+between)\b", lower):
            dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
            d1 = dates[0] if len(dates) >= 1 else "2026-01-01"
            d2 = dates[1] if len(dates) >= 2 else "2026-12-31"
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Calculate number of days between {d1} and {d2}",
                    tool_name="datetime_tool",
                    arguments={"action": "diff", "date1": d1, "date2": d2},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        if any(k in lower for k in ["what time is it", "current time", "today's date", "current date", "what day is it", "timezone"]):
            tz_match = re.search(r"in\s+([a-zA-Z_]+(?:/[a-zA-Z_]+)?)", text, re.IGNORECASE)
            tz = tz_match.group(1) if tz_match else None
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Query current date and time{' in ' + tz if tz else ''}",
                    tool_name="datetime_tool",
                    arguments={"action": "now", "timezone": tz} if tz else {"action": "now"},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 3. File Listing and Reading tasks
        if re.search(r"\b(?:find|list|show|get)\s+(?:all\s+)?(?:the\s+)?(?:python|\.py)?\s*files\b", lower) or any(k in lower for k in ["list files", "show files", "workspace files", "dir", "directory tree"]):
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description="Find and list files in permitted workspace",
                    tool_name="workspace_list_files",
                    arguments={"recursive": True, "max_depth": 3},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 4. File Creation tasks
        create_file_match = re.search(
            r"(?:create|write|save to)\s+(?:a\s+)?file\s+(?:called\s+|named\s+)?([^\s,]+)(?:\s+(?:in\s+workspace|in\s+directory))?(?:\s+(?:with\s+content|with)\s+['\"]?([\s\S]+))?",
            text,
            re.IGNORECASE,
        )
        if create_file_match:
            filename = create_file_match.group(1).strip("\"' ")
            content = create_file_match.group(2) or ""
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Create workspace file '{filename}'",
                    tool_name="workspace_create_file",
                    arguments={"path": filename, "content": content, "overwrite": True},
                    risk_level=RiskLevel.MEDIUM,
                    dependencies=[]
                )
            )
            return steps

        # 5. File Reading tasks
        read_file_match = re.search(r"(?:read|open|view|inspect|show)\s+(?:the\s+)?file\s+([^\s,]+)", text, re.IGNORECASE)
        if read_file_match:
            filename = read_file_match.group(1).strip("\"' ")
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Read workspace file '{filename}'",
                    tool_name="workspace_read_file",
                    arguments={"path": filename},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 6. Calculator / Math tasks
        math_trigger = re.search(r"\b(?:calculate|compute|solve|what is)\b|\b\d+\s*[\+\-\*\/%]\s*\d+\b|\b\d+%\s*(?:of|\*)\s*\d+\b|\b(?:sqrt|sin|cos|log)\s*\(", text, re.IGNORECASE)
        if math_trigger:
            math_match = re.search(r"(?:calculate|compute|solve|what is)\s+(.+)", text, re.IGNORECASE)
            expr = text
            if math_match:
                expr = math_match.group(1).rstrip("?.!")
            expr = re.sub(r"^(?:calculate|compute|solve|what is)\s+", "", expr, flags=re.IGNORECASE).strip()
            expr = re.sub(r"\s+(?:and\s+)?(?:explain|tell me|show work|show the result|detail|summarize|please).*$", "", expr, flags=re.IGNORECASE).strip()
            if expr:
                steps.append(
                    TaskStepPlan(
                        step_number=1,
                        description=f"Calculate arithmetic expression: '{expr}'",
                        tool_name="calculator",
                        arguments={"expression": expr},
                        risk_level=RiskLevel.LOW,
                        dependencies=[]
                    )
                )
                return steps

        # 3. File Creation tasks
        create_file_match = re.search(r"(?:create|write|save to)\s+(?:a\s+)?file\s+(?:called\s+|named\s+)?([^\s,]+)(?:\s+(?:with\s+content|with)\s+['\"]?([\s\S]+?)['\"]?)?$", text, re.IGNORECASE)
        if create_file_match:
            filename = create_file_match.group(1).strip("\"' ")
            content = create_file_match.group(2) or ""
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Create workspace file '{filename}'",
                    tool_name="workspace_create_file",
                    arguments={"path": filename, "content": content, "overwrite": True},
                    risk_level=RiskLevel.MEDIUM,
                    dependencies=[]
                )
            )
            return steps

        # 4. File Reading tasks
        read_file_match = re.search(r"(?:read|open|view|inspect|show)\s+(?:the\s+)?file\s+([^\s,]+)", text, re.IGNORECASE)
        if read_file_match:
            filename = read_file_match.group(1).strip("\"' ")
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Read workspace file '{filename}'",
                    tool_name="workspace_read_file",
                    arguments={"path": filename},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 5. File Listing tasks
        if any(k in lower for k in ["list files", "show files", "workspace files", "dir", "directory tree"]):
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description="List workspace files and directories",
                    tool_name="workspace_list_files",
                    arguments={"recursive": True, "max_depth": 3},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 6. Search / Research tasks
        if any(k in lower for k in ["search for", "look up", "research", "find information about"]):
            query_match = re.search(r"(?:search for|look up|research|find information about)\s+['\"]?([\s\S]+?)['\"]?$", text, re.IGNORECASE)
            search_query = query_match.group(1).strip() if query_match else text
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Search research knowledge for: '{search_query}'",
                    tool_name="research_search",
                    arguments={"query": search_query, "max_results": 5},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 7. Code Inspection & Symbol search
        if any(k in lower for k in ["inspect codebase", "code structure", "analyze project"]):
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description="Inspect project codebase structure",
                    tool_name="code_inspect_structure",
                    arguments={"directory": "", "max_depth": 3},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        symbol_match = re.search(r"(?:find|search)\s+(?:symbol|function|class|method)\s+([a-zA-Z0-9_]+)", text, re.IGNORECASE)
        if symbol_match:
            sym_name = symbol_match.group(1)
            steps.append(
                TaskStepPlan(
                    step_number=1,
                    description=f"Search codebase for symbol '{sym_name}'",
                    tool_name="code_search_symbols",
                    arguments={"query": sym_name, "symbol_type": "all"},
                    risk_level=RiskLevel.LOW,
                    dependencies=[]
                )
            )
            return steps

        # 8. Multi-step sequence or fallback based on suggested tools
        if intent_result and intent_result.suggested_tools:
            for idx, tool_name in enumerate(intent_result.suggested_tools, 1):
                if self._registry.has(tool_name):
                    tool = self._registry.get(tool_name)
                    steps.append(
                        TaskStepPlan(
                            step_number=idx,
                            description=f"Execute {tool.name} for request: {goal[:50]}",
                            tool_name=tool.name,
                            arguments={},
                            risk_level=tool.risk_level,
                            dependencies=[idx - 1] if idx > 1 else []
                        )
                    )

        return steps
