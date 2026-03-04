"""Provider-backed chat completion clients without external dependencies."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .config import Settings


class LLMError(RuntimeError):
    """Raised when model communication fails."""


def _http_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 120) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise LLMError(f"HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise LLMError(f"Connection failed: {error}") from error


def _openai_api_key(settings: Settings) -> str:
    return settings.extra.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")


def _openai_base_url(settings: Settings) -> str:
    return settings.extra.get("openai_base_url", "https://api.openai.com/v1")


def openai_chat(messages: list[dict[str, str]], settings: Settings) -> str:
    api_key = _openai_api_key(settings)
    if not api_key:
        raise LLMError("Missing OpenAI API key. Set OPENAI_API_KEY or flexcoder settings openai_api_key <key>.")

    payload = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature,
        "max_tokens": settings.max_output_tokens,
        "top_p": settings.top_p,
        "frequency_penalty": settings.frequency_penalty,
        "presence_penalty": settings.presence_penalty,
    }
    data = _http_json(
        f"{_openai_base_url(settings).rstrip('/')}/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LLMError(f"Unexpected OpenAI response: {json.dumps(data)}") from error


def _ollama_base_url(settings: Settings) -> str:
    return settings.extra.get("ollama_base_url", "http://127.0.0.1:11434")


def ollama_chat(messages: list[dict[str, str]], settings: Settings) -> str:
    payload = {
        "model": settings.model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "num_predict": settings.max_output_tokens,
            "frequency_penalty": settings.frequency_penalty,
            "presence_penalty": settings.presence_penalty,
        },
    }
    data = _http_json(f"{_ollama_base_url(settings).rstrip('/')}/api/chat", payload, headers={})

    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as error:
        raise LLMError(f"Unexpected Ollama response: {json.dumps(data)}") from error


def provider_chat(messages: list[dict[str, str]], settings: Settings) -> str:
    provider = settings.provider.lower().strip()
    if provider == "openai":
        return openai_chat(messages, settings)
    if provider == "ollama":
        return ollama_chat(messages, settings)
    raise LLMError(
        f"Unsupported provider '{settings.provider}'. Use 'flexcoder providers openai' or 'flexcoder providers ollama'."
    )
