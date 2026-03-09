"""providers.py — provider registry (built-in + custom) and live model fetching.

Verified endpoints (March 2026):
  OpenAI     GET https://api.openai.com/v1/models              Authorization: Bearer KEY
  Anthropic  GET https://api.anthropic.com/v1/models           x-api-key + anthropic-version
  Gemini     GET https://generativelanguage.googleapis.com/v1beta/models?key=KEY
  Mistral    GET https://api.mistral.ai/v1/models               Authorization: Bearer KEY
  OpenRouter GET https://openrouter.ai/api/v1/models            Authorization: Bearer KEY
  Ollama     GET http://localhost:11434/api/tags                (no auth)
"""

import requests

# ── Built-in providers ────────────────────────────────────────────────────────
# "name" is the display name (no emoji — use plain text for cross-platform compatibility)

PROVIDERS: dict[str, dict] = {
    "ollama": {
        "name":      "Ollama",
        "color":     "#5588dd",
        "needs_key":  False,
        "key_cfg":    None,
        "builtin":    True,
    },
    "claude": {
        "name":      "Claude",
        "color":     "orange3",
        "needs_key":  True,
        "key_cfg":    "anthropic",
        "builtin":    True,
    },
    "chatgpt": {
        "name":      "ChatGPT",
        "color":     "green3",
        "needs_key":  True,
        "key_cfg":    "openai",
        "builtin":    True,
    },
    "gemini": {
        "name":      "Gemini",
        "color":     "dodger_blue1",
        "needs_key":  True,
        "key_cfg":    "gemini",
        "builtin":    True,
    },
    "mistral": {
        "name":      "Mistral",
        "color":     "magenta",
        "needs_key":  True,
        "key_cfg":    "mistral",
        "builtin":    True,
    },
    "openrouter": {
        "name":      "OpenRouter",
        "color":     "yellow3",
        "needs_key":  True,
        "key_cfg":    "openrouter",
        "builtin":    True,
    },
}

PROVIDER_KEYS = list(PROVIDERS.keys())


def _reload_custom(doc) -> None:
    """Load custom providers from config into the PROVIDERS dict."""
    global PROVIDER_KEYS
    custom = doc.get("custom_providers", {})
    for key, info in custom.items():
        if key not in PROVIDERS:
            PROVIDERS[key] = {
                "name":      str(info.get("name", key)),
                "color":     str(info.get("color", "white")),
                "needs_key": bool(info.get("needs_key", False)),
                "key_cfg":   str(info.get("key_cfg", key)),
                "base_url":  str(info.get("base_url", "")),
                "models_url":str(info.get("models_url", "")),
                "builtin":   False,
            }
    PROVIDER_KEYS = list(PROVIDERS.keys())


def fetch_models(provider_key: str, api_key: str = "") -> tuple[list[str], str | None]:
    """Fetch live model list. Returns (models, error_or_None)."""
    try:
        info = PROVIDERS.get(provider_key, {})
        # Custom (non-builtin) provider
        if not info.get("builtin", True):
            return _fetch_custom(info, api_key)
        match provider_key:
            case "ollama":     return _ollama()
            case "claude":     return _anthropic(api_key)
            case "chatgpt":    return _openai(api_key)
            case "gemini":     return _gemini(api_key)
            case "mistral":    return _mistral(api_key)
            case "openrouter": return _openrouter(api_key)
            case "groq":       return _groq(api_key)
            case "deepseek":   return _deepseek(api_key)
            case "cohere":     return _cohere(api_key)
            case "perplexity": return _perplexity(api_key)
            case "xai":        return _xai(api_key)
            case "together":   return _together(api_key)
            case _:            return [], f"Unknown provider: {provider_key}"
    except requests.exceptions.ConnectionError as e:
        return [], f"Connection error: {e}"
    except requests.exceptions.Timeout:
        return [], "Request timed out"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        try:
            detail = e.response.json()
        except Exception:
            detail = {}
        msg = detail.get("error", {}).get("message", "") or str(e)
        return [], f"HTTP {code}: {msg}"
    except Exception as e:
        return [], str(e)


# ── Per-provider fetchers ─────────────────────────────────────────────────────

def _ollama() -> tuple[list[str], str | None]:
    r = requests.get("http://localhost:11434/api/tags", timeout=10)
    r.raise_for_status()
    models = [m["name"] for m in r.json().get("models", [])]
    if not models:
        return [], "No models found — is Ollama running? (`ollama serve`)"
    return sorted(models), None


def _anthropic(api_key: str) -> tuple[list[str], str | None]:
    if not api_key:
        return [], "API key required"
    r = requests.get(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=15,
    )
    r.raise_for_status()
    ids = [m["id"] for m in r.json().get("data", [])]
    return sorted(ids), None


def _openai(api_key: str) -> tuple[list[str], str | None]:
    if not api_key:
        return [], "API key required"
    r = requests.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    r.raise_for_status()
    ids = sorted(
        [m["id"] for m in r.json().get("data", [])
         if any(p in m["id"] for p in ("gpt", "o1", "o3", "o4"))],
        reverse=True,
    )
    return ids, None


def _gemini(api_key: str) -> tuple[list[str], str | None]:
    if not api_key:
        return [], "API key required"
    r = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        timeout=15,
    )
    r.raise_for_status()
    ids = [
        m["name"].replace("models/", "")
        for m in r.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    return sorted(ids), None


def _mistral(api_key: str) -> tuple[list[str], str | None]:
    if not api_key:
        return [], "API key required"
    r = requests.get(
        "https://api.mistral.ai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    r.raise_for_status()
    ids = sorted([m["id"] for m in r.json().get("data", [])])
    return ids, None


def _openrouter(api_key: str) -> tuple[list[str], str | None]:
    if not api_key:
        return [], "API key required"
    r = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    r.raise_for_status()
    ids = sorted([m["id"] for m in r.json().get("data", [])])
    return ids, None



def _groq(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    r = requests.get("https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    return sorted([m["id"] for m in r.json().get("data", [])]), None

def _deepseek(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    r = requests.get("https://api.deepseek.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    return sorted([m["id"] for m in r.json().get("data", [])]), None

def _cohere(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    r = requests.get("https://api.cohere.com/v2/models",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    return sorted([m["name"] for m in r.json().get("models", [])]), None

def _perplexity(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    # Perplexity doesn't have a /models endpoint — return known models
    return ["llama-3.1-sonar-small-128k-online", "llama-3.1-sonar-large-128k-online",
            "llama-3.1-sonar-huge-128k-online"], None

def _xai(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    r = requests.get("https://api.x.ai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    return sorted([m["id"] for m in r.json().get("data", [])]), None

def _together(api_key: str) -> tuple[list[str], str | None]:
    if not api_key: return [], "API key required"
    r = requests.get("https://api.together.xyz/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
    r.raise_for_status()
    return sorted([m["id"] for m in r.json() if isinstance(m, dict)]), None

def _fetch_custom(info: dict, api_key: str) -> tuple[list[str], str | None]:
    """Fetch models from a custom OpenAI-compatible endpoint."""
    url = info.get("models_url", "")
    if not url:
        return [], "No models URL configured for this provider"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    # Try OpenAI-style {data: [{id: ...}]} first, then flat list
    if "data" in data:
        ids = [m["id"] for m in data["data"]]
    elif "models" in data:
        ids = [m.get("id") or m.get("name", "") for m in data["models"]]
    elif isinstance(data, list):
        ids = [m.get("id") or m.get("name", "") for m in data]
    else:
        return [], "Unrecognised model list format"
    return sorted(filter(None, ids)), None


# ── Extended built-in providers (models.dev supported) ────────────────────────
# Added after original definition so existing config isn't broken

def _add_extended_providers():
    extra = {
        "groq": {
            "name":      "Groq",
            "color":     "bright_red",
            "needs_key":  True,
            "key_cfg":    "groq",
            "builtin":    True,
        },
        "deepseek": {
            "name":      "DeepSeek",
            "color":     "deep_sky_blue1",
            "needs_key":  True,
            "key_cfg":    "deepseek",
            "builtin":    True,
        },
        "cohere": {
            "name":      "Cohere",
            "color":     "sandy_brown",
            "needs_key":  True,
            "key_cfg":    "cohere",
            "builtin":    True,
        },
        "perplexity": {
            "name":      "Perplexity",
            "color":     "turquoise2",
            "needs_key":  True,
            "key_cfg":    "perplexity",
            "builtin":    True,
        },
        "xai": {
            "name":      "xAI (Grok)",
            "color":     "grey84",
            "needs_key":  True,
            "key_cfg":    "xai",
            "builtin":    True,
        },
        "together": {
            "name":      "Together AI",
            "color":     "medium_purple1",
            "needs_key":  True,
            "key_cfg":    "together",
            "builtin":    True,
        },
    }
    for key, info in extra.items():
        if key not in PROVIDERS:
            PROVIDERS[key] = info
    global PROVIDER_KEYS
    PROVIDER_KEYS = list(PROVIDERS.keys())

_add_extended_providers()
