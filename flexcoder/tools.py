"""tools.py — execute AI tool calls and return their output to the chat.

Safety rules:
  - search_replace and insert REQUIRE the file to have been read first this session.
  - shell commands outside the working directory require explicit user approval.
"""

from __future__ import annotations
import re
import os
import subprocess
import shutil
from pathlib import Path


# ── Tool result container ─────────────────────────────────────────────────────

class ToolResult:
    def __init__(self, tool: str, ok: bool, output: str,
                 needs_approval: bool = False, approval_prompt: str = ""):
        self.tool            = tool
        self.ok              = ok
        self.output          = output
        self.needs_approval  = needs_approval
        self.approval_prompt = approval_prompt

    def __str__(self) -> str:
        status = "✔" if self.ok else "✘"
        return f"[{self.tool}] {status}\n{self.output}" if self.output else f"[{self.tool}] {status}"


# ── Session-level read tracker ────────────────────────────────────────────────

_read_files: set[str] = set()   # absolute paths read this session

def mark_read(path: str) -> None:
    _read_files.add(str(Path(path).resolve()))

def was_read(path: str) -> bool:
    return str(Path(path).resolve()) in _read_files

def reset_session() -> None:
    _read_files.clear()


# ── Parser ────────────────────────────────────────────────────────────────────

_TOOL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("create_file",       re.compile(r'<create_file=(.+?)>(.*?)</create_file>',  re.DOTALL)),
    ("move_file",         re.compile(r'<move_file\s+source=(.+?)\s+destination=(.+?)\s*/>')),
    ("read_file",         re.compile(r'<read_file=(.+?)\s*/>')),
    ("create_directory",  re.compile(r'<create_directory=(.+?)\s*/>')),
    ("search_replace",    re.compile(
        r'<search_replace=(.+?)><search>(.*?)</search><replace>(.*?)</replace></search_replace>',
        re.DOTALL)),
    ("shell",             re.compile(r'<shell>(.*?)</shell>', re.DOTALL)),
    ("insert",            re.compile(
        r'<insert=(.+?)><for>(.*?)</for><after>(.*?)</after><text>(.*?)</text></insert>',
        re.DOTALL)),
]


def parse_tools(text: str) -> list[tuple[str, tuple]]:
    """Find all tool calls in text. Returns list of (tool_name, groups)."""
    found = []
    for name, pat in _TOOL_PATTERNS:
        for m in pat.finditer(text):
            found.append((m.start(), name, m.groups()))
    found.sort(key=lambda x: x[0])
    return [(name, groups) for _, name, groups in found]


def execute(tool: str, groups: tuple, cwd: str,
            outside_cwd_approved: bool = False) -> ToolResult:
    """Execute one tool call and return the result."""
    try:
        match tool:
            case "create_file":      return _create_file(groups, cwd)
            case "move_file":        return _move_file(groups, cwd)
            case "read_file":        return _read_file(groups, cwd)
            case "create_directory": return _create_directory(groups, cwd)
            case "search_replace":   return _search_replace(groups, cwd)
            case "shell":            return _shell(groups, cwd, outside_cwd_approved)
            case "insert":           return _insert(groups, cwd)
            case _:                  return ToolResult(tool, False, f"Unknown tool: {tool}")
    except Exception as e:
        return ToolResult(tool, False, str(e))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve(path_str: str, cwd: str) -> Path:
    p = Path(path_str.strip())
    return p if p.is_absolute() else Path(cwd) / p

def _is_outside_cwd(path: Path, cwd: str) -> bool:
    try:
        path.resolve().relative_to(Path(cwd).resolve())
        return False
    except ValueError:
        return True


# ── Tool implementations ──────────────────────────────────────────────────────

def _create_file(g: tuple, cwd: str) -> ToolResult:
    path, content = g
    target = _resolve(path, cwd)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return ToolResult("create_file", True, f"Created: {target}")


def _move_file(g: tuple, cwd: str) -> ToolResult:
    src, dst = g
    s = _resolve(src, cwd)
    d = _resolve(dst, cwd)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return ToolResult("move_file", True, f"Moved: {s} → {d}")


def _read_file(g: tuple, cwd: str) -> ToolResult:
    path   = g[0]
    target = _resolve(path, cwd)
    if not target.exists():
        return ToolResult("read_file", False, f"File not found: {target}")
    content = target.read_text(encoding="utf-8", errors="replace")
    mark_read(str(target))
    return ToolResult("read_file", True, content)


def _create_directory(g: tuple, cwd: str) -> ToolResult:
    path   = g[0]
    target = _resolve(path, cwd)
    target.mkdir(parents=True, exist_ok=True)
    return ToolResult("create_directory", True, f"Directory created: {target}")


def _search_replace(g: tuple, cwd: str) -> ToolResult:
    path, search, replace = g
    target = _resolve(path, cwd)
    if not target.exists():
        return ToolResult("search_replace", False, f"File not found: {target}")
    # Safety: must have been read first
    if not was_read(str(target)):
        return ToolResult(
            "search_replace", False,
            f"Safety: {target.name} must be read first before editing. "
            f"Use <read_file={path} /> first."
        )
    original = target.read_text(encoding="utf-8")
    if search not in original:
        return ToolResult("search_replace", False, f"Search text not found in {target}")
    updated = original.replace(search, replace, 1)
    target.write_text(updated, encoding="utf-8")
    return ToolResult("search_replace", True, f"Replaced in: {target}")


def _shell(g: tuple, cwd: str, outside_approved: bool) -> ToolResult:
    cmd = g[0].strip()

    # Safety: check if command tries to cd outside cwd or uses absolute paths outside cwd
    # Heuristic: look for absolute paths not under cwd, or explicit cd ..
    suspicious = False
    cwd_resolved = str(Path(cwd).resolve())
    # Check for 'cd' to outside
    import re as _re
    cd_match = _re.search(r'\bcd\s+([^\s;&|]+)', cmd)
    if cd_match:
        dest = cd_match.group(1)
        try:
            resolved = str(Path(cwd, dest).resolve())
            if not resolved.startswith(cwd_resolved):
                suspicious = True
        except Exception:
            pass

    if suspicious and not outside_approved:
        return ToolResult(
            "shell", False, "",
            needs_approval=True,
            approval_prompt=(
                f"The command wants to go outside the working directory:\n"
                f"  {cmd}\n"
                f"Allow? (Press Enter to approve, Esc to deny)"
            )
        )

    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=60,
    )
    output = (result.stdout or "") + (result.stderr or "")
    ok = result.returncode == 0
    return ToolResult("shell", ok, output.strip() or "(no output)")


def _insert(g: tuple, cwd: str) -> ToolResult:
    path, context_before, context_after, text = g
    target = _resolve(path, cwd)
    if not target.exists():
        return ToolResult("insert", False, f"File not found: {target}")
    # Safety: must have been read first
    if not was_read(str(target)):
        return ToolResult(
            "insert", False,
            f"Safety: {target.name} must be read first before editing. "
            f"Use <read_file={path} /> first."
        )
    original = target.read_text(encoding="utf-8")
    lines    = original.splitlines(keepends=True)

    if not context_before.strip() and not context_after.strip():
        target.write_text(text + "".join(lines), encoding="utf-8")
        return ToolResult("insert", True, f"Inserted at beginning of {target}")

    before_lines = [l.rstrip("\n") for l in context_before.strip().splitlines()]
    after_lines  = [l.rstrip("\n") for l in context_after.strip().splitlines()]
    stripped     = [l.rstrip("\n") for l in lines]
    insert_at    = None

    for i in range(len(stripped)):
        if before_lines:
            seg = stripped[i: i + len(before_lines)]
            if seg == before_lines:
                candidate = i + len(before_lines)
                if after_lines:
                    seg2 = stripped[candidate: candidate + len(after_lines)]
                    if seg2 == after_lines:
                        insert_at = candidate
                        break
                else:
                    insert_at = candidate
                    break
        elif after_lines:
            seg = stripped[i: i + len(after_lines)]
            if seg == after_lines:
                insert_at = i
                break

    if insert_at is None:
        return ToolResult("insert", False, "Context not found in file")

    lines.insert(insert_at, text if text.endswith("\n") else text + "\n")
    target.write_text("".join(lines), encoding="utf-8")
    return ToolResult("insert", True,
        f"Inserted {len(text.splitlines())} line(s) at line {insert_at + 1} of {target}")
