"""Filesystem path helpers."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = ".flexcoder"


def user_profile_dir() -> Path:
    """Return USERPROFILE directory (or fallback home)."""
    profile = os.environ.get("USERPROFILE")
    if profile:
        return Path(profile).expanduser().resolve()
    return Path.home().resolve()


def app_data_dir() -> Path:
    """Return app data directory and ensure it exists."""
    root = user_profile_dir() / APP_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def logs_dir() -> Path:
    """Return chat log directory and ensure it exists."""
    directory = app_data_dir() / "chatlogs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
