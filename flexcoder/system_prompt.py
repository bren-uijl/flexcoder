"""system_prompt.py — build the system prompt sent to every AI call."""

from __future__ import annotations
import os
import platform
import subprocess
from pathlib import Path


def _detect_shell() -> str:
    shell = os.environ.get("SHELL", "")
    if shell:
        return Path(shell).name
    # Windows
    if os.environ.get("PSModulePath"):
        return "PowerShell"
    if os.environ.get("COMSPEC"):
        return "cmd.exe"
    return "unknown"


def _tree(cwd: str, max_depth: int = 3, max_items: int = 60) -> str:
    """Simple directory tree — no external dependencies."""
    lines = [cwd]
    count = [0]

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth or count[0] >= max_items:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if count[0] >= max_items:
                lines.append(f"{prefix}... (truncated)")
                return
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            count[0] += 1
            if entry.is_dir() and not entry.name.startswith("."):
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)

    _walk(Path(cwd), "", 1)
    return "\n".join(lines)


TOOLS_DOC = """\
You have the following tools available. Use at most ONE tool per response,
and it MUST appear at the very end of your response.

Create a file:
  <create_file=[path]>content</create_file>

Move/rename a file:
  <move_file source=[old_path] destination=[new_path] />

Read a file:
  <read_file=[path] />

Create a directory:
  <create_directory=[path] />

Search and replace in a file (replaces first occurrence):
  <search_replace=[file]><search>old text</search><replace>new text</replace></search_replace>

Run a shell command:
  <shell>command</shell>

Insert text into a file (provide 5 lines of context before/after, or leave blank):
  <insert=[file]><for>[5 lines before, or empty if beginning]</for><after>[5 lines after, or empty if end]</after><text>[text to insert]</text></insert>

Rules:
- Always start your response with "i see".
- Use at most ONE tool per response.
- The tool call MUST be the last thing in your response.
- After a tool call you will receive the tool output automatically.
"""


def build(cwd: str, extra: str = "") -> str:
    os_name   = platform.system()
    os_ver    = platform.version()
    arch      = platform.machine()
    shell     = _detect_shell()
    tree_text = _tree(cwd)

    parts = [
        f"You are flexcoder, an expert AI coding assistant running inside a TUI.",
        f"",
        f"## Environment",
        f"OS:    {os_name} {os_ver} ({arch})",
        f"Shell: {shell}",
        f"CWD:   {cwd}",
        f"",
        f"## Project tree",
        f"```",
        tree_text,
        f"```",
        f"",
        TOOLS_DOC,
    ]

    if extra and extra.strip():
        parts += ["", "## Additional instructions", extra.strip()]

    return "\n".join(parts)
