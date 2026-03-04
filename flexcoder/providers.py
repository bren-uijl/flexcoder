"""Provider and model command handlers."""

from __future__ import annotations

from .config import ConfigStore


SUPPORTED_PROVIDERS = ("openai", "ollama")


def set_provider(provider: str) -> str:
    normalized = provider.lower().strip()
    if normalized not in SUPPORTED_PROVIDERS:
        return f"Unsupported provider: {provider}. Available: {', '.join(SUPPORTED_PROVIDERS)}"

    store = ConfigStore()
    settings = store.load()
    settings.provider = normalized
    if normalized == "openai" and settings.model in {"default", "gemma3:3b"}:
        settings.model = "gpt-4o-mini"
    if normalized == "ollama" and settings.model in {"default", "gpt-4o-mini"}:
        settings.model = "gemma3:3b"
    store.save(settings)
    return f"Selected provider: {settings.provider}\nSelected model: {settings.model}"


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


def provider_help() -> str:
    return (
        "Available providers:\n"
        "- openai (uses OPENAI_API_KEY or setting openai_api_key)\n"
        "- ollama (uses local server, default http://127.0.0.1:11434)\n\n"
        "Usage:\n"
        "flexcoder providers openai\n"
        "flexcoder providers ollama"
    )
