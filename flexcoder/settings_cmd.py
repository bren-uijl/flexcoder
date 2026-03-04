"""Settings command helpers."""

from __future__ import annotations

from dataclasses import asdict

from .config import ConfigStore


NUMERIC_FIELDS = {
    "temperature": float,
    "max_output_tokens": int,
    "top_p": float,
    "frequency_penalty": float,
    "presence_penalty": float,
}


def list_settings() -> str:
    settings = ConfigStore().load()
    pairs = asdict(settings)
    lines = [f"{k}={v}" for k, v in pairs.items()]
    return "\n".join(lines)


def set_setting(key: str, value: str) -> str:
    store = ConfigStore()
    settings = store.load()

    if key in NUMERIC_FIELDS:
        cast = NUMERIC_FIELDS[key]
        setattr(settings, key, cast(value))
    elif hasattr(settings, key):
        setattr(settings, key, value)
    else:
        settings.extra[key] = value

    store.save(settings)
    return f"Updated {key}={value}"
