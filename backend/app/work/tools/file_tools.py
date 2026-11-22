"""
Workspace File Tools for Universal Work Intelligence (Phase 05).
Implements safe workspace file inspection, reading, creation, editing, and searching
with strict path traversal guards and sensitive file protection.
"""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config.settings import get_settings
from backend.app.work.exceptions import PathTraversalError, SensitiveFileAccessError
from backend.app.work.schemas import PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool

# Blocklist of sensitive file patterns that must never be accessed or modified
BLOCKED_PATTERNS = [
    ".env*",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "*.crt",
    "*secret*",
    "*token*",
    "*credential*",
    "*password*",
    "id_rsa*",
    "id_ed25519*",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "love.db*",
    ".git*",
    ".venv*",
]

BLOCKED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
}


def get_workspace_root() -> Path:
    """Resolves and ensures the safe workspace root directory."""
    settings = get_settings()
    configured = settings.WORKSPACE_ROOT
    path = Path(configured)
    if not path.is_absolute():
        from backend.app.config.settings import BASE_DIR
        path = (BASE_DIR / configured).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_and_resolve_path(rel_or_abs_path: str, workspace_root: Optional[Path] = None) -> Path:
    """
    Validates that a path is strictly confined within the workspace root
    and does not match blocked sensitive file patterns.
    """
    ws = (workspace_root or get_workspace_root()).resolve()
    target = (ws / rel_or_abs_path).resolve()

    # 1. Confinement check
    try:
        common = Path(os.path.commonpath([ws, target])).resolve()
        if common != ws:
            raise PathTraversalError(
                f"Security violation: path '{rel_or_abs_path}' resolves outside workspace boundary '{ws}'"
            )
    except ValueError:
        raise PathTraversalError(
            f"Security violation: path '{rel_or_abs_path}' resolves on a different drive or invalid path."
        )

    # 2. Blocked path segments check
    for part in target.parts:
        if part in BLOCKED_DIR_NAMES:
            raise SensitiveFileAccessError(f"Access to directory '{part}' is restricted.")

    # 3. Blocked file patterns check
    filename = target.name
    for pattern in BLOCKED_PATTERNS:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            raise SensitiveFileAccessError(
                f"Access to sensitive or restricted file '{filename}' is prohibited."
            )

    return target


class WorkspaceListFilesTool(BaseTool):
    """Lists files and directories confined within the workspace."""

    @property
    def name(self) -> str:
        return "workspace_list_files"

    @property
    def description(self) -> str:
        return "Lists files and directories in the workspace or a sub-folder. Read-only and path-confined."

    @property
    def category(self) -> str:
        return "file"

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
                    "description": "Subdirectory relative to workspace root (defaults to workspace root)",
                    "default": ""
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively",
                    "default": False
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum recursive traversal depth",
                    "default": 3
                }
            }
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        sub_dir = kwargs.get("directory", "")
        recursive = bool(kwargs.get("recursive", False))
        max_depth = int(kwargs.get("max_depth", 3))

        ws = get_workspace_root()
        target_dir = validate_and_resolve_path(sub_dir, ws)

        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: '{sub_dir}'")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is a file, not a directory: '{sub_dir}'")

        entries: List[Dict[str, Any]] = []

        if not recursive:
            for item in sorted(target_dir.iterdir()):
                # Skip blocked directories
                if item.name in BLOCKED_DIR_NAMES:
                    continue
                # Skip blocked patterns
                if any(fnmatch.fnmatch(item.name.lower(), p.lower()) for p in BLOCKED_PATTERNS):
                    continue

                rel = item.relative_to(ws).as_posix()
                entries.append({
                    "name": item.name,
                    "path": rel,
                    "is_directory": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                })
        else:
            base_parts_len = len(target_dir.parts)
            for root, dirs, files in os.walk(target_dir):
                curr_path = Path(root)
                depth = len(curr_path.parts) - base_parts_len
                if depth >= max_depth:
                    dirs.clear()
                    continue

                # Filter dirs in-place
                dirs[:] = [
                    d for d in dirs
                    if d not in BLOCKED_DIR_NAMES and not any(fnmatch.fnmatch(d.lower(), p.lower()) for p in BLOCKED_PATTERNS)
                ]

                for f in files:
                    if any(fnmatch.fnmatch(f.lower(), p.lower()) for p in BLOCKED_PATTERNS):
                        continue
                    item = curr_path / f
                    rel = item.relative_to(ws).as_posix()
                    entries.append({
                        "name": f,
                        "path": rel,
                        "is_directory": False,
                        "size_bytes": item.stat().st_size if item.is_file() else None,
                    })

        return {
            "workspace_root": str(ws),
            "directory": sub_dir,
            "total_items": len(entries),
            "items": entries[:200],  # Cap output at 200 items for safety
        }


class WorkspaceReadFileTool(BaseTool):
    """Reads file content from the workspace safely."""

    @property
    def name(self) -> str:
        return "workspace_read_file"

    @property
    def description(self) -> str:
        return "Reads file content from the workspace with line range limits and safe byte capping."

    @property
    def category(self) -> str:
        return "file"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path inside workspace"},
                "start_line": {"type": "integer", "description": "1-based starting line number", "default": 1},
                "end_line": {"type": "integer", "description": "1-based ending line number (inclusive)"},
                "max_bytes": {"type": "integer", "description": "Maximum bytes to read", "default": 100000}
            },
            "required": ["path"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        rel_path = kwargs.get("path")
        if not rel_path:
            raise ValueError("Parameter 'path' is required.")

        start_line = max(1, int(kwargs.get("start_line", 1)))
        end_line = kwargs.get("end_line")
        end_line = int(end_line) if end_line is not None else None
        max_bytes = int(kwargs.get("max_bytes", 100000))

        ws = get_workspace_root()
        target_file = validate_and_resolve_path(rel_path, ws)

        if not target_file.exists():
            raise FileNotFoundError(f"File not found: '{rel_path}'")
        if not target_file.is_file():
            raise IsADirectoryError(f"Target '{rel_path}' is a directory, not a file.")

        total_size = target_file.stat().st_size

        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            raise IOError(f"Failed to read file '{rel_path}': {e}")

        total_lines = len(lines)
        end_idx = min(end_line if end_line is not None else total_lines, total_lines)
        selected_lines = lines[start_line - 1:end_idx]
        content = "".join(selected_lines)

        truncated = False
        if len(content.encode("utf-8")) > max_bytes:
            content = content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
            truncated = True

        return {
            "path": rel_path,
            "total_lines": total_lines,
            "total_bytes": total_size,
            "start_line": start_line,
            "end_line": end_idx,
            "content": content,
            "truncated": truncated
        }


class WorkspaceCreateFileTool(BaseTool):
    """Creates a new file or overwrites an existing one in the workspace."""

    @property
    def name(self) -> str:
        return "workspace_create_file"

    @property
    def description(self) -> str:
        return "Creates or writes a file in the workspace. Path-confined and protected against sensitive overwrites."

    @property
    def category(self) -> str:
        return "file"

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
                "path": {"type": "string", "description": "Relative file path inside workspace to create"},
                "content": {"type": "string", "description": "Content string to write into the file"},
                "overwrite": {"type": "boolean", "description": "Whether to allow overwriting existing file", "default": False}
            },
            "required": ["path", "content"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        rel_path = kwargs.get("path")
        content = kwargs.get("content", "")
        overwrite = bool(kwargs.get("overwrite", False))

        if not rel_path:
            raise ValueError("Parameter 'path' is required.")

        ws = get_workspace_root()
        target_file = validate_and_resolve_path(rel_path, ws)

        existed = target_file.exists()
        if existed and not overwrite:
            raise FileExistsError(
                f"File '{rel_path}' already exists and 'overwrite' is False. Set overwrite=True to replace."
            )

        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "path": rel_path,
            "bytes_written": len(content.encode("utf-8")),
            "existed_previously": existed,
            "message": f"Successfully {'updated' if existed else 'created'} file '{rel_path}'."
        }


class WorkspaceEditFileTool(BaseTool):
    """Edits an existing file in the workspace using target/replacement string matching."""

    @property
    def name(self) -> str:
        return "workspace_edit_file"

    @property
    def description(self) -> str:
        return "Replaces text in a workspace file using exact target string matching. Safe and path-confined."

    @property
    def category(self) -> str:
        return "file"

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
                "path": {"type": "string", "description": "Relative file path inside workspace to edit"},
                "target_string": {"type": "string", "description": "Exact text substring to find and replace"},
                "replacement_string": {"type": "string", "description": "New replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences if true, else first occurrence", "default": False}
            },
            "required": ["path", "target_string", "replacement_string"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        rel_path = kwargs.get("path")
        target_string = kwargs.get("target_string")
        replacement_string = kwargs.get("replacement_string", "")
        replace_all = bool(kwargs.get("replace_all", False))

        if not rel_path or target_string is None:
            raise ValueError("Parameters 'path' and 'target_string' are required.")

        ws = get_workspace_root()
        target_file = validate_and_resolve_path(rel_path, ws)

        if not target_file.exists():
            raise FileNotFoundError(f"File not found: '{rel_path}'")

        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()

        count = content.count(target_string)
        if count == 0:
            raise ValueError(f"Target string not found in file '{rel_path}'.")

        if replace_all:
            new_content = content.replace(target_string, replacement_string)
            replacements_made = count
        else:
            new_content = content.replace(target_string, replacement_string, 1)
            replacements_made = 1

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "path": rel_path,
            "occurrences_found": count,
            "occurrences_replaced": replacements_made,
            "new_size_bytes": len(new_content.encode("utf-8")),
            "message": f"Successfully replaced {replacements_made} occurrence(s) in '{rel_path}'."
        }


class WorkspaceSearchFilesTool(BaseTool):
    """Searches file contents within the workspace."""

    @property
    def name(self) -> str:
        return "workspace_search_files"

    @property
    def description(self) -> str:
        return "Searches file contents across workspace files matching a query or regex pattern."

    @property
    def category(self) -> str:
        return "file"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text substring or regex pattern to search for"},
                "directory": {"type": "string", "description": "Subdirectory to restrict search within", "default": ""},
                "file_pattern": {"type": "string", "description": "Glob pattern for filenames (e.g. '*.py', '*.md')", "default": "*"},
                "is_regex": {"type": "boolean", "description": "Whether query is a regex pattern", "default": False},
                "max_results": {"type": "integer", "description": "Maximum match items to return", "default": 50}
            },
            "required": ["query"]
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            raise ValueError("Parameter 'query' is required.")

        sub_dir = kwargs.get("directory", "")
        file_glob = kwargs.get("file_pattern", "*")
        is_regex = bool(kwargs.get("is_regex", False))
        max_results = int(kwargs.get("max_results", 50))

        ws = get_workspace_root()
        search_root = validate_and_resolve_path(sub_dir, ws)

        compiled_re = re.compile(query, re.IGNORECASE) if is_regex else None
        matches: List[Dict[str, Any]] = []

        for root, dirs, files in os.walk(search_root):
            # Exclude blocked dirs
            dirs[:] = [
                d for d in dirs
                if d not in BLOCKED_DIR_NAMES and not any(fnmatch.fnmatch(d.lower(), p.lower()) for p in BLOCKED_PATTERNS)
            ]

            for fname in files:
                if not fnmatch.fnmatch(fname, file_glob):
                    continue
                if any(fnmatch.fnmatch(fname.lower(), p.lower()) for p in BLOCKED_PATTERNS):
                    continue

                fpath = Path(root) / fname
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            matched = False
                            if compiled_re:
                                if compiled_re.search(line):
                                    matched = True
                            else:
                                if query.lower() in line.lower():
                                    matched = True

                            if matched:
                                rel = fpath.relative_to(ws).as_posix()
                                matches.append({
                                    "file": rel,
                                    "line_number": line_num,
                                    "line": line.strip()[:200]
                                })
                                if len(matches) >= max_results:
                                    break
                except Exception:
                    continue

                if len(matches) >= max_results:
                    break
            if len(matches) >= max_results:
                break

        return {
            "query": query,
            "total_matches": len(matches),
            "matches": matches,
        }
