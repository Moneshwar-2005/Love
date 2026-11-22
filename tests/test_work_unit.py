"""
Unit Tests for Phase 05 Universal Work Intelligence and Safe Tool Orchestration.
Covers tools, path traversal security, sensitive file blocking, permissions,
task planning, execution, and intent classification.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from backend.app.intelligence.intent import IntentClassifier
from backend.app.intelligence.schemas import TaskIntent
from backend.app.work.exceptions import (
    PathTraversalError,
    SensitiveFileAccessError,
    ToolNotFoundError,
    ToolPermissionDeniedError,
)
from backend.app.work.executor import TaskExecutor
from backend.app.work.permissions import PermissionManager
from backend.app.work.planner import TaskPlanner
from backend.app.work.schemas import ApprovalState, RiskLevel
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
    validate_and_resolve_path,
)
from backend.app.work.tools.registry import ToolRegistry
from backend.app.work.tools.research_tool import MockResearchProvider, ResearchSearchTool


# ==============================================================================
# 1. Calculator Tool Tests
# ==============================================================================

class TestCalculatorTool:
    @pytest.mark.asyncio
    async def test_basic_arithmetic(self):
        tool = CalculatorTool()
        res = await tool.run(expression="15 + 27 * 2")
        assert res["result"] == 69
        assert res["expression"] == "15 + 27 * 2"

    @pytest.mark.asyncio
    async def test_advanced_math_functions(self):
        tool = CalculatorTool()
        res_sqrt = await tool.run(expression="sqrt(144) + abs(-8)")
        assert res_sqrt["result"] == 20.0

        res_perc = await tool.run(expression="25% of 200")
        assert res_perc["result"] == 50.0

    @pytest.mark.asyncio
    async def test_rejection_of_arbitrary_code_injection(self):
        tool = CalculatorTool()
        with pytest.raises(ValueError) as exc:
            await tool.run(expression="__import__('os').system('echo pwned')")
        assert "Security restriction" in str(exc.value)

        with pytest.raises(ValueError):
            await tool.run(expression="open('love.db', 'r')")

        with pytest.raises(ValueError):
            await tool.run(expression="exec('x = 1')")

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        tool = CalculatorTool()
        with pytest.raises(ValueError) as exc:
            await tool.run(expression="100 / 0")
        assert "Division by zero" in str(exc.value)


# ==============================================================================
# 2. DateTime Tool Tests
# ==============================================================================

class TestDateTimeTool:
    @pytest.mark.asyncio
    async def test_current_time(self):
        tool = DateTimeTool()
        res = await tool.run(action="now", timezone="UTC")
        assert res["action"] == "now"
        assert "iso_timestamp" in res
        assert "day_of_week" in res
        assert res["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_date_difference(self):
        tool = DateTimeTool()
        res = await tool.run(action="diff", date1="2026-01-01", date2="2026-01-10")
        assert res["diff_days"] == 9
        assert res["diff_total_seconds"] == 9 * 86400

    @pytest.mark.asyncio
    async def test_date_add_subtract(self):
        tool = DateTimeTool()
        res_add = await tool.run(action="add", date1="2026-01-01T00:00:00", days=5, hours=2)
        assert "2026-01-06T02:00:00" in res_add["result_timestamp"]

        res_sub = await tool.run(action="subtract", date1="2026-01-10T12:00:00", days=3)
        assert "2026-01-07T12:00:00" in res_sub["result_timestamp"]


# ==============================================================================
# 3. File Security and Path Traversal Tests
# ==============================================================================

class TestFileToolsAndSecurity:
    @pytest.fixture
    def test_ws(self, tmp_path):
        ws = tmp_path / "test_workspace"
        ws.mkdir()
        return ws

    def test_path_confinement_and_traversal_prevention(self, test_ws):
        # Normal path inside workspace is valid
        resolved = validate_and_resolve_path("sub/file.txt", workspace_root=test_ws)
        assert resolved == (test_ws / "sub" / "file.txt").resolve()

        # Path traversal attempts must be blocked
        with pytest.raises(PathTraversalError):
            validate_and_resolve_path("../outside.txt", workspace_root=test_ws)

        with pytest.raises(PathTraversalError):
            validate_and_resolve_path("sub/../../escaped.txt", workspace_root=test_ws)

    def test_sensitive_file_blocking(self, test_ws):
        # Sensitive extensions and names must be blocked
        sensitive_files = [
            ".env",
            ".env.production",
            "server.pem",
            "private.key",
            "id_rsa",
            "id_ed25519",
            "app_secret.txt",
            "user_token.json",
            "love.db",
            "database.sqlite3",
        ]
        for f in sensitive_files:
            with pytest.raises(SensitiveFileAccessError):
                validate_and_resolve_path(f, workspace_root=test_ws)

        # Blocked directories
        with pytest.raises(SensitiveFileAccessError):
            validate_and_resolve_path(".git/config", workspace_root=test_ws)
        with pytest.raises(SensitiveFileAccessError):
            validate_and_resolve_path(".venv/bin/python", workspace_root=test_ws)

    @pytest.mark.asyncio
    async def test_workspace_file_operations(self, monkeypatch, test_ws):
        from backend.app.work.tools import file_tools
        monkeypatch.setattr(file_tools, "get_workspace_root", lambda: test_ws)

        create_tool = WorkspaceCreateFileTool()
        read_tool = WorkspaceReadFileTool()
        edit_tool = WorkspaceEditFileTool()
        list_tool = WorkspaceListFilesTool()
        search_tool = WorkspaceSearchFilesTool()

        # 1. Create file
        create_res = await create_tool.run(path="notes.txt", content="Hello LOVE Agent\nLine 2\nLine 3", overwrite=True)
        assert create_res["bytes_written"] > 0

        # 2. Read file
        read_res = await read_tool.run(path="notes.txt", start_line=1, end_line=2)
        assert "Hello LOVE Agent" in read_res["content"]
        assert read_res["total_lines"] == 3

        # 3. Edit file
        edit_res = await edit_tool.run(
            path="notes.txt",
            target_string="LOVE Agent",
            replacement_string="Super Assistant",
        )
        assert edit_res["occurrences_replaced"] == 1

        # Verify edited content
        verify_read = await read_tool.run(path="notes.txt")
        assert "Super Assistant" in verify_read["content"]

        # 4. Search files
        search_res = await search_tool.run(query="Super Assistant")
        assert search_res["total_matches"] >= 1

        # 5. List files
        list_res = await list_tool.run(directory="")
        assert any(item["name"] == "notes.txt" for item in list_res["items"])


# ==============================================================================
# 4. Research Provider Interface Tests
# ==============================================================================

class TestResearchTool:
    @pytest.mark.asyncio
    async def test_mock_research_provider(self):
        provider = MockResearchProvider()
        assert provider.is_available is True
        findings = await provider.search(query="Python asyncio architecture", max_results=2)
        assert len(findings) >= 1
        assert "Python asyncio architecture" in findings[0].query

    @pytest.mark.asyncio
    async def test_research_search_tool(self):
        tool = ResearchSearchTool(provider=MockResearchProvider())
        res = await tool.run(query="FastAPI concurrency")
        assert res["total_findings"] >= 1
        assert len(res["citations"]) >= 1
        assert res["provider"] == "mock"


# ==============================================================================
# 5. Coding Workspace Tools Tests
# ==============================================================================

class TestCodingTools:
    @pytest.fixture
    def code_ws(self, tmp_path):
        ws = tmp_path / "code_ws"
        ws.mkdir()
        py_file = ws / "sample.py"
        py_file.write_text(
            "class Engine:\n    def start(self):\n        return True\n\nasync def compute_data():\n    return 42\n",
            encoding="utf-8"
        )
        return ws

    @pytest.mark.asyncio
    async def test_code_inspection_and_symbol_search(self, monkeypatch, code_ws):
        from backend.app.work.tools import file_tools
        monkeypatch.setattr(file_tools, "get_workspace_root", lambda: code_ws)

        inspect_tool = CodeInspectStructureTool()
        symbols_tool = CodeSearchSymbolsTool()
        propose_tool = CodeProposeChangesTool()
        apply_tool = CodeApplyPatchTool()

        # 1. Inspect structure
        inspect_res = await inspect_tool.run(directory="")
        assert inspect_res["total_files"] >= 1
        assert ".py" in inspect_res["extension_breakdown"]

        # 2. Search symbols (AST parsed)
        sym_res = await symbols_tool.run(query="Engine")
        assert sym_res["total_found"] >= 1
        assert sym_res["symbols"][0]["name"] == "Engine"
        assert sym_res["symbols"][0]["type"] == "class"

        func_res = await symbols_tool.run(query="compute_data")
        assert func_res["total_found"] >= 1
        assert func_res["symbols"][0]["type"] == "async_function"

        # 3. Propose changes (diff without write)
        prop_res = await propose_tool.run(
            path="sample.py",
            proposed_content="class Engine:\n    def start(self):\n        return 'updated'\n",
        )
        assert prop_res["has_changes"] is True
        assert "--- a/sample.py" in prop_res["unified_diff"]

        # 4. Apply patch
        apply_res = await apply_tool.run(
            path="sample.py",
            content="# Patched\nx = 100\n",
            create_backup=True,
        )
        assert apply_res["bytes_written"] > 0
        assert (code_ws / "sample.py.bak").exists()


# ==============================================================================
# 6. Tool Registry Tests
# ==============================================================================

class TestToolRegistry:
    def test_default_registration(self):
        reg = ToolRegistry()
        tools = reg.list_tools()
        assert len(tools) >= 10
        assert reg.has("calculator")
        assert reg.has("datetime_tool")
        assert reg.has("workspace_read_file")
        assert reg.has("research_search")
        assert reg.has("code_search_symbols")

    def test_filtering(self):
        reg = ToolRegistry()
        math_tools = reg.list_tools(category="math")
        assert len(math_tools) >= 1
        assert math_tools[0].name == "calculator"

        low_risk = reg.list_tools(max_risk=RiskLevel.LOW)
        for t in low_risk:
            assert t.risk_level == RiskLevel.LOW

    def test_not_found(self):
        reg = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            reg.get("non_existent_tool_123")


# ==============================================================================
# 7. Permission Manager Tests
# ==============================================================================

class TestPermissionManager:
    def test_permission_levels(self):
        calc = CalculatorTool()
        create = WorkspaceCreateFileTool()

        pm = PermissionManager(require_medium_confirmation=True)
        assert pm.requires_approval(calc) is False
        assert pm.requires_approval(create) is True

        # Low risk auto-permits
        permitted, _ = pm.evaluate_permission(calc)
        assert permitted is True

        # Medium risk without approval is denied
        permitted, reason = pm.evaluate_permission(create, approval_state=ApprovalState.PENDING)
        assert permitted is False
        assert "requires user confirmation" in reason

        # Medium risk with approved state is permitted
        permitted, _ = pm.evaluate_permission(create, approval_state=ApprovalState.APPROVED)
        assert permitted is True

    def test_validate_execution_guard_raises(self):
        create = WorkspaceCreateFileTool()
        pm = PermissionManager(require_medium_confirmation=True)
        with pytest.raises(ToolPermissionDeniedError):
            pm.validate_execution_guard(create, approval_state=ApprovalState.PENDING)


# ==============================================================================
# 8. Task Planner Tests
# ==============================================================================

class TestTaskPlanner:
    def test_plan_calculator_task(self):
        planner = TaskPlanner()
        steps = planner.plan_task("Calculate 45 * 12 + 100")
        assert len(steps) == 1
        assert steps[0].tool_name == "calculator"
        assert steps[0].arguments["expression"] == "45 * 12 + 100"

    def test_plan_datetime_task(self):
        planner = TaskPlanner()
        steps = planner.plan_task("What time is it in UTC?")
        assert len(steps) == 1
        assert steps[0].tool_name == "datetime_tool"
        assert steps[0].arguments.get("timezone") == "UTC"

    def test_plan_file_creation_task(self):
        planner = TaskPlanner()
        steps = planner.plan_task("Create a file called summary.md with content # Overview")
        assert len(steps) == 1
        assert steps[0].tool_name == "workspace_create_file"
        assert steps[0].arguments["path"] == "summary.md"
        assert "# Overview" in steps[0].arguments["content"]


# ==============================================================================
# 9. Intent Classification Enhancement Tests
# ==============================================================================

class TestIntentClassificationEnhancement:
    def test_intent_action_requirement(self):
        # Action required
        r1 = IntentClassifier.classify("Calculate 15% of 850")
        assert r1.requires_action is True
        assert "calculator" in r1.suggested_tools

        r2 = IntentClassifier.classify("Create a file called data.txt")
        assert r2.requires_action is True
        assert "workspace_create_file" in r2.suggested_tools

        r3 = IntentClassifier.classify("What time is it in Tokyo?")
        assert r3.requires_action is True
        assert "datetime_tool" in r3.suggested_tools

        # Pure conversational - no action required
        r_conv = IntentClassifier.classify("Hi, how are you today?")
        assert r_conv.requires_action is False
        assert len(r_conv.suggested_tools) == 0

        r_info = IntentClassifier.classify("What is quantum computing?")
        assert r_info.requires_action is False

    def test_ambiguity_detection(self):
        r_amb = IntentClassifier.classify("calculate")
        assert r_amb.is_ambiguous is True
        assert r_amb.clarification_prompt is not None
