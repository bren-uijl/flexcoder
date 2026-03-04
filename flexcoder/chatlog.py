"""Chat log persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .paths import logs_dir


class ChatLogStore:
    """Store messages in USERPROFILE/.flexcoder/chatlogs."""

    def __init__(self) -> None:
        self._dir = logs_dir()

    def create_session_path(self) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return self._dir / f"session-{stamp}.jsonl"

    def append(self, path: Path, role: str, content: str) -> None:
        row = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "role": role,
            "content": content,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def latest(self) -> Path | None:
        logs = sorted(self._dir.glob("session-*.jsonl"))
        if not logs:
            return None
        return logs[-1]
