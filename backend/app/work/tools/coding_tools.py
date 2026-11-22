"""
Coding Workspace Tools for Universal Work Intelligence (Phase 05).
Provides static codebase structural inspection, symbol searching, diff generation,
and safe patch application within the workspace boundary.
STRICT GUARD: Arbitrary code execution and subprocess shells are prohibited.
"""

import ast
import difflib
import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.work.exceptions import PathTraversalError, SensitiveFileAccessError
from backend.app.work.schemas import PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool
from backend.app.work.tools import file_tools


class CodeInspectStructureTool(BaseTool):
    """Inspects workspace project hierarchy and source file composition."""

    @property
    def name(self) -> str:
        return "code_inspect_structure"

    @property
    def description(self) -> str:
        return (
            "Analyzes code directory structure, file hierarchy, file counts by extension, "
            "and estimated lines of code within the workspace."
        )

    @property
    def category(self) -> str:
        return "code"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory relative to workspace root (defaults to root)",
                    "default": ""
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory traversal depth",
                    "default": 3
                }
            }
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        sub_dir = kwargs.get("directory", "")
        max_depth = int(kwargs.get("max_depth", 3))

        ws = file_tools.get_workspace_root()
        target_dir = file_tools.validate_and_resolve_path(sub_dir, ws)

        if not target_dir.is_dir():
            raise NotADirectoryError(f"Target '{sub_dir}' is not a directory.")

        tree_nodes: List[Dict[str, Any]] = []
        extension_counts: Dict[str, int] = {}
        total_files = 0
        total_loc = 0

        base_parts_len = len(target_dir.parts)

        for root, dirs, files in os.walk(target_dir):
            curr_path = Path(root)
            depth = len(curr_path.parts) - base_parts_len
            if depth >= max_depth:
                dirs.clear()
                continue

            dirs[:] = [
                d for d in dirs
                if d not in file_tools.BLOCKED_DIR_NAMES and not any(fnmatch.fnmatch(d.lower(), p.lower()) for p in file_tools.BLOCKED_PATTERNS)
            ]

            for fname in files:
                if any(fnmatch.fnmatch(fname.lower(), p.lower()) for p in file_tools.BLOCKED_PATTERNS):
                    continue

                fpath = curr_path / fname
                ext = fpath.suffix.lower() or "no_ext"
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
                total_files += 1

                # Sample line counts for text code files
                loc = 0
                if ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".txt", ".sql", ".sh"}:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            loc = sum(1 for _ in f)
                            total_loc += loc
                    except Exception:
                        pass

                rel = fpath.relative_to(ws).as_posix()
                tree_nodes.append({
                    "path": rel,
                    "name": fname,
                    "extension": ext,
                    "lines_of_code": loc,
                    "size_bytes": fpath.stat().st_size
                })

        return {
            "root_inspected": sub_dir or ".",
            "total_files": total_files,
            "total_estimated_loc": total_loc,
            "extension_breakdown": extension_counts,
            "structure_sample": tree_nodes[:100]
        }


class CodeSearchSymbolsTool(BaseTool):
    """Extracts and searches for class and function symbols in workspace source files."""

    @property
    def name(self) -> str:
        return "code_search_symbols"

    @property
    def description(self) -> str:
        return (
            "Searches for function, method, and class definitions across workspace code files. "
            "Uses AST parsing for Python and regex patterns for other source languages."
        )

    @property
    def category(self) -> str:
        return "code"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Symbol name or substring to search for (e.g. 'execute', 'User', 'process')"
                },
                "symbol_type": {
                    "type": "string",
                    "enum": ["all", "function", "class", "async_function"],
                    "default": "all"
                },
                "directory": {
                    "type": "string",
                    "description": "Directory relative to workspace",
                    "default": ""
                }
            },
            "required": ["query"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "").lower()
        symbol_type = kwargs.get("symbol_type", "all")
        sub_dir = kwargs.get("directory", "")

        if not query:
            raise ValueError("Parameter 'query' is required.")

        ws = file_tools.get_workspace_root()
        target_dir = file_tools.validate_and_resolve_path(sub_dir, ws)

        symbols: List[Dict[str, Any]] = []

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [
                d for d in dirs
                if d not in file_tools.BLOCKED_DIR_NAMES and not any(fnmatch.fnmatch(d.lower(), p.lower()) for p in file_tools.BLOCKED_PATTERNS)
            ]

            for fname in files:
                if any(fnmatch.fnmatch(fname.lower(), p.lower()) for p in file_tools.BLOCKED_PATTERNS):
                    continue
                fpath = Path(root) / fname
                rel = fpath.relative_to(ws).as_posix()

                if fname.endswith(".py"):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            code_text = f.read()
                        tree = ast.parse(code_text, filename=fname)

                        for node in ast.walk(tree):
                            name = ""
                            kind = ""
                            line = getattr(node, "lineno", 0)

                            if isinstance(node, ast.FunctionDef):
                                name = node.name
                                kind = "function"
                            elif isinstance(node, ast.AsyncFunctionDef):
                                name = node.name
                                kind = "async_function"
                            elif isinstance(node, ast.ClassDef):
                                name = node.name
                                kind = "class"

                            if name and (query in name.lower()):
                                if symbol_type == "all" or symbol_type == kind:
                                    symbols.append({
                                        "name": name,
                                        "type": kind,
                                        "file": rel,
                                        "line": line
                                    })
                    except Exception:
                        pass

                elif fname.endswith((".js", ".ts", ".jsx", ".tsx")):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                # Regex match function, class, const func
                                m = re.search(r'\b(class|function|async function|const|let)\s+([a-zA-Z0-9_$]+)', line)
                                if m:
                                    kind = m.group(1)
                                    name = m.group(2)
                                    if query in name.lower():
                                        symbols.append({
                                            "name": name,
                                            "type": kind,
                                            "file": rel,
                                            "line": idx
                                        })
                    except Exception:
                        pass

        return {
            "query": query,
            "total_found": len(symbols),
            "symbols": symbols[:100]
        }


class CodeProposeChangesTool(BaseTool):
    """Generates a structured unified diff representation for proposed code modifications."""

    @property
    def name(self) -> str:
        return "code_propose_changes"

    @property
    def description(self) -> str:
        return (
            "Generates a unified diff comparing existing file content against proposed new content. "
            "Does not write to disk (read-only diff generation)."
        )

    @property
    def category(self) -> str:
        return "code"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path inside workspace"},
                "proposed_content": {"type": "string", "description": "Complete new content proposed for the file"}
            },
            "required": ["path", "proposed_content"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        rel_path = kwargs.get("path")
        proposed_content = kwargs.get("proposed_content", "")

        if not rel_path:
            raise ValueError("Parameter 'path' is required.")

        ws = file_tools.get_workspace_root()
        target_file = file_tools.validate_and_resolve_path(rel_path, ws)

        original_lines = []
        if target_file.exists():
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                original_lines = f.readlines()

        proposed_lines = [line + "\n" if not line.endswith("\n") else line for line in proposed_content.splitlines()]

        diff = difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm=""
        )
        diff_text = "\n".join(diff)

        return {
            "path": rel_path,
            "exists": target_file.exists(),
            "has_changes": bool(diff_text.strip()),
            "unified_diff": diff_text
        }


class CodeApplyPatchTool(BaseTool):
    """Applies a patch or proposed full content to a workspace file with safety validation."""

    @property
    def name(self) -> str:
        return "code_apply_patch"

    @property
    def description(self) -> str:
        return (
            "Applies validated changes to a workspace file. Requires user confirmation. "
            "Strictly confined to workspace boundaries."
        )

    @property
    def category(self) -> str:
        return "code"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.REQUIRES_CONFIRMATION

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path inside workspace to update"},
                "content": {"type": "string", "description": "New content to save"},
                "create_backup": {"type": "boolean", "description": "Create backup (.bak) before writing", "default": True}
            },
            "required": ["path", "content"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        rel_path = kwargs.get("path")
        content = kwargs.get("content", "")
        create_backup = bool(kwargs.get("create_backup", True))

        if not rel_path:
            raise ValueError("Parameter 'path' is required.")

        ws = file_tools.get_workspace_root()
        target_file = file_tools.validate_and_resolve_path(rel_path, ws)

        if target_file.exists() and create_backup:
            backup_path = target_file.with_suffix(target_file.suffix + ".bak")
            try:
                backup_path.write_bytes(target_file.read_bytes())
            except Exception:
                pass

        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "path": rel_path,
            "bytes_written": len(content.encode("utf-8")),
            "backup_created": create_backup and target_file.exists(),
            "message": f"Successfully applied changes to '{rel_path}'."
        }
