"""modelsdev.py — fetch and cache model data from models.dev API.

The API lives at https://models.dev/api.json and returns a dict keyed by
provider id. Each value has {id, name, models: {model_id: {...model data}}}.

We cache the result in ~/.flexcoder/modelsdev_cache.json for 24h.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

import requests

_CACHE_FILE  = Path.home() / ".flexcoder" / "modelsdev_cache.json"
_CACHE_TTL   = 86400   # 24 hours
_API_URL     = "https://models.dev/api.json"

# Providers we know how to call — map models.dev id → our provider key
_SUPPORTED_PROVIDERS = {
    "anthropic":  "claude",
    "openai":     "chatgpt",
    "google":     "gemini",
    "mistral":    "mistral",
    "groq":       "groq",
    "deepseek":   "deepseek",
    "cohere":     "cohere",
    "openrouter": "openrouter",
    "perplexity": "perplexity",
    "xai":        "xai",
    "meta":       "meta",
    "amazon-bedrock": "bedrock",
}


# ── Public API ────────────────────────────────────────────────────────────────

def fetch(force: bool = False) -> dict[str, Any]:
    """Return the full models.dev database. Uses cache when fresh."""
    if not force and _cache_valid():
        try:
            return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _download()
    if data:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(
            json.dumps({"_ts": time.time(), "data": data}), encoding="utf-8"
        )
        return data
    # Fall back to stale cache if download fails
    if _CACHE_FILE.exists():
        try:
            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            return raw.get("data", {})
        except Exception:
            pass
    return {}


def get_providers(db: dict) -> list[dict]:
    """Return list of {id, name, model_count} sorted by name."""
    out = []
    for pid, pinfo in db.items():
        out.append({
            "id":          pid,
            "name":        pinfo.get("name", pid),
            "model_count": len(pinfo.get("models", {})),
        })
    return sorted(out, key=lambda x: x["name"].lower())


def get_models_for_provider(db: dict, provider_id: str) -> list[dict]:
    """Return list of model dicts for a given provider, sorted by name."""
    pinfo  = db.get(provider_id, {})
    models = pinfo.get("models", {})
    out    = []
    for mid, minfo in models.items():
        # Skip deprecated
        if minfo.get("status") == "deprecated":
            continue
        out.append({
            "id":          minfo.get("id", f"{provider_id}/{mid}"),
            "name":        minfo.get("name", mid),
            "context":     minfo.get("limit", {}).get("context", 0),
            "output":      minfo.get("limit", {}).get("output", 0),
            "input_cost":  minfo.get("cost", {}).get("input", 0),
            "output_cost": minfo.get("cost", {}).get("output", 0),
            "tool_call":   minfo.get("tool_call", False),
            "reasoning":   minfo.get("reasoning", False),
            "open_weights":minfo.get("open_weights", False),
        })
    return sorted(out, key=lambda x: x["name"].lower())


def our_provider_key(models_dev_id: str) -> str | None:
    """Convert a models.dev provider id to our internal provider key."""
    return _SUPPORTED_PROVIDERS.get(models_dev_id)


def format_context(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens // 1_000_000}M"
    if tokens >= 1_000:
        return f"{tokens // 1_000}K"
    return str(tokens) if tokens else "?"


def format_cost(per_m: float) -> str:
    if per_m == 0:
        return "free"
    if per_m < 0.01:
        return f"${per_m:.4f}"
    return f"${per_m:.2f}"


# ── Internal ──────────────────────────────────────────────────────────────────

def _cache_valid() -> bool:
    if not _CACHE_FILE.exists():
        return False
    try:
        raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        return (time.time() - raw.get("_ts", 0)) < _CACHE_TTL
    except Exception:
        return False


def _download() -> dict | None:
    try:
        r = requests.get(_API_URL, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
