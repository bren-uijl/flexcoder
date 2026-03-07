"""sessions.py — session persistence in ~/.flexcoder/sessions/."""

import json
import uuid
import datetime
from pathlib import Path
from flexcoder.config import SESSIONS_DIR


def new_id() -> str:
    ts    = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    short = str(uuid.uuid4())[:6]
    return f"{ts}-{short}"


def _file(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def load(session_id: str) -> dict | None:
    f = _file(session_id)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save(
    session_id: str,
    provider: str,
    model: str,
    cwd: str,
    messages: list[dict],
) -> None:
    data = {
        "session_id": session_id,
        "provider":   provider,
        "model":      model,
        "cwd":        cwd,
        "created":    datetime.datetime.now().isoformat(),
        "messages":   messages,
    }
    _file(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_all() -> list[dict]:
    out = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            msgs = d.get("messages", [])
            out.append({
                "id":       f.stem,
                "provider": d.get("provider", "?"),
                "model":    d.get("model", "?"),
                "cwd":      d.get("cwd", "?"),
                "count":    len(msgs),
                "last":     msgs[-1].get("content", "")[:70] if msgs else "",
                "created":  d.get("created", ""),
            })
        except Exception:
            pass
    return out
