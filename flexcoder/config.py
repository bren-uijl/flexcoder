"""config.py — TOML-based persistent configuration."""

import os
import tomlkit
from pathlib import Path

# Prefer $USERPROFILE (Windows) then $HOME (Unix)
_home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
CONFIG_DIR   = _home / ".flexcoder"
SESSIONS_DIR = CONFIG_DIR / "sessions"
CONFIG_FILE  = CONFIG_DIR / "config.toml"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Defaults ──────────────────────────────────────────────────────────────────

_DEFAULTS: dict = {
    "general": {
        "provider":     "ollama",
        "model":        "",          # no default — must be chosen
        "auto_approve": True,
        "show_output":  False,
    },
    "api_keys": {
        "anthropic":   "",
        "openai":      "",
        "gemini":      "",
        "mistral":     "",
        "openrouter":  "",
    },
    "models": {
        # Populated by "Fetch Models". Start empty.
        "ollama":      [],
        "claude":      [],
        "chatgpt":     [],
        "gemini":      [],
        "mistral":     [],
        "openrouter":  [],
    },
    "ai_settings": {
        "temperature":  1.0,
        "max_tokens":   4096,
        "top_p":        1.0,
        "top_k":        -1,       # -1 = not set
        "stream":       False,
        "system_prompt": "",      # extra user-defined system prompt addendum
    },
}


# ── Load / save ───────────────────────────────────────────────────────────────

def load() -> tomlkit.TOMLDocument:
    if CONFIG_FILE.exists():
        try:
            doc = tomlkit.parse(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            doc = tomlkit.parse("")
    else:
        doc = tomlkit.parse("")

    # Merge defaults — add missing keys without overwriting existing values
    for section, values in _DEFAULTS.items():
        if section not in doc:
            t = tomlkit.table()
            doc.add(section, t)
        for k, v in values.items():
            if k not in doc[section]:
                doc[section][k] = v
    return doc


def save(doc: tomlkit.TOMLDocument) -> None:
    CONFIG_FILE.write_text(tomlkit.dumps(doc), encoding="utf-8")


# ── Convenience helpers ───────────────────────────────────────────────────────

def get(doc: tomlkit.TOMLDocument, *keys):
    val = doc
    for k in keys:
        try:
            val = val[k]
        except (KeyError, TypeError):
            return None
    # unwrap tomlkit types to plain Python
    if hasattr(val, "_trivia"):
        return val.unwrap() if hasattr(val, "unwrap") else val
    return val


def set_val(doc: tomlkit.TOMLDocument, section: str, key: str, value) -> None:
    if section not in doc:
        doc.add(section, tomlkit.table())
    doc[section][key] = value


def get_api_key(doc: tomlkit.TOMLDocument, provider_key: str) -> str:
    """Return stored key, falling back to environment variable."""
    _env_map = {
        "claude":     "ANTHROPIC_API_KEY",
        "chatgpt":    "OPENAI_API_KEY",
        "gemini":     "GEMINI_API_KEY",
        "mistral":    "MISTRAL_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    stored = get(doc, "api_keys", provider_key) or ""
    if isinstance(stored, str) and stored.strip():
        return stored.strip()
    env = _env_map.get(provider_key, "")
    return os.environ.get(env, "") if env else ""


def get_models(doc: tomlkit.TOMLDocument, provider_key: str) -> list[str]:
    m = get(doc, "models", provider_key)
    if isinstance(m, list):
        return [str(x) for x in m]
    return []


def set_models(doc: tomlkit.TOMLDocument, provider_key: str, models: list[str]) -> None:
    if "models" not in doc:
        doc.add("models", tomlkit.table())
    arr = tomlkit.array()
    for m in models:
        arr.append(m)
    doc["models"][provider_key] = arr
