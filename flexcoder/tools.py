"""Minimal tool execution helpers."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


def run_shell(command: str, cwd: Path) -> str:
    """Run shell command and return captured output."""
    process = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    output = []
    if process.stdout.strip():
        output.append(process.stdout.strip())
    if process.stderr.strip():
        output.append(process.stderr.strip())
    output.append(f"exit_code={process.returncode}")
    return "\n".join(output)


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def create_file(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"created: {path}"


def create_directory(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    return f"created directory: {path}"


def move_file(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)
    return f"moved: {source} -> {destination}"


def parse_shell_tag(text: str) -> str | None:
    opener = "<shell>"
    closer = "</shell>"
    if opener in text and closer in text:
        return text.split(opener, 1)[1].split(closer, 1)[0].strip()
    return None


def safe_split(command: str) -> list[str]:
    return shlex.split(command)
