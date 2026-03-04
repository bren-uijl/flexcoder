"""System prompt builder."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

TOOL_DOC = """Available tools and usage:
- Create file: <create_file=[path]>content</create_file>
- Move file: <move_file source=[old_path] destination=[new_path] />
- Read file: <read_file=[path] />
- Create directory: <create_directory=[path] />
- Search/replace: <search_replace=file><search>old text</search><replace>new text</replace></search_replace>
- Shell: <shell>[command]</shell>
- Insert text: <insert=file><for>[5 lines or empty for start]</for><after>[5 lines or empty for end]</after><text>[text to insert]</text></insert>
"""


def _detect_shell() -> str:
    return os.environ.get("SHELL") or os.environ.get("COMSPEC") or "unknown shell"


def _directory_tree(path: Path) -> str:
    try:
        result = subprocess.run(
            ["tree", "-a", "-L", "2", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass

    lines = [f"{path.name}/"]
    for entry in sorted(path.iterdir(), key=lambda p: p.name)[:40]:
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"  - {entry.name}{suffix}")
    return "\n".join(lines)


def build_system_prompt(cwd: Path) -> str:
    """Create system prompt with environment + tool rules."""
    os_name = platform.platform()
    shell = _detect_shell()
    tree_text = _directory_tree(cwd)

    return (
        "You are FlexCoder, an expert coding assistant for real software tasks.\n"
        f"Operating system: {os_name}\n"
        f"Shell: {shell}\n"
        "Current directory tree:\n"
        f"{tree_text}\n\n"
        f"{TOOL_DOC}\n"
        "Response format constraints:\n"
        "1) Start every response with exactly: i see\n"
        "2) Use at most one tool per response.\n"
        "3) If you use a tool, it must appear at the end of the response.\n"
        "4) If you use a tool, include a short explanation before the tool call.\n"
        "5) Be specific, non-repetitive, and directly solve the user's request.\n"
    )
