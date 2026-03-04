"""Configuration storage for FlexCoder."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import app_data_dir


@dataclass
class Settings:
    provider: str = "ollama"
    model: str = "gemma3:3b"
    temperature: float = 0.2
    max_output_tokens: int = 1024
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    extra: dict[str, str] = field(default_factory=dict)


class ConfigStore:
    """Persist user settings as JSON."""

    def __init__(self) -> None:
        self._path = app_data_dir() / "config.json"

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        defaults = Settings()
        merged = asdict(defaults)
        merged.update(data)
        return Settings(**merged)

    def save(self, settings: Settings) -> None:
        self._path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
