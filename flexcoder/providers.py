"""Provider and model command handlers."""

from __future__ import annotations

from .config import ConfigStore


def set_provider(provider: str) -> str:
    store = ConfigStore()
    settings = store.load()
    settings.provider = provider
    store.save(settings)
    return f"Selected provider: {provider}"


def set_model(model: str) -> str:
    store = ConfigStore()
    settings = store.load()
    settings.model = model
    store.save(settings)
    return f"Selected model: {model}"


def set_ollama_model(model: str) -> str:
    store = ConfigStore()
    settings = store.load()
    settings.provider = "ollama"
    settings.model = model
    store.save(settings)
    return f"Selected provider: ollama\nSelected model: {model}"
