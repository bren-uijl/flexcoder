"""ai.py — send messages to the active provider."""

from __future__ import annotations
import os


def chat(
    provider: str,
    model: str,
    messages: list[dict],
    api_key: str,
    system_prompt: str,
    temperature: float = 1.0,
    max_tokens: int = 4096,
    top_p: float = 1.0,
    top_k: int = -1,
) -> tuple[str | None, str | None]:
    """
    Returns (reply_text, error_or_None).
    messages: list of {"role": "user"|"assistant", "content": str}
    """
    try:
        match provider:
            case "ollama":     return _ollama(model, messages, system_prompt, temperature, max_tokens)
            case "claude":     return _anthropic(model, messages, api_key, system_prompt, temperature, max_tokens, top_p, top_k)
            case "chatgpt":    return _openai(model, messages, api_key, system_prompt, temperature, max_tokens, top_p)
            case "gemini":     return _gemini(model, messages, api_key, system_prompt, temperature, max_tokens, top_p, top_k)
            case "mistral":    return _mistral(model, messages, api_key, system_prompt, temperature, max_tokens, top_p)
            case "openrouter": return _openrouter(model, messages, api_key, system_prompt, temperature, max_tokens, top_p)
            case _:            return None, f"Unknown provider: {provider}"
    except Exception as e:
        return None, str(e)


# ── Providers ─────────────────────────────────────────────────────────────────

def _ollama(model, messages, system, temperature, max_tokens):
    import requests
    payload = {
        "model":   model,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream":  False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", ""), None


def _anthropic(model, messages, api_key, system, temperature, max_tokens, top_p, top_k):
    import anthropic
    kw: dict = dict(temperature=temperature, top_p=top_p)
    if top_k > 0:
        kw["top_k"] = top_k
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": m["role"], "content": m["content"]}
                  for m in messages if m["role"] in ("user", "assistant")],
        **kw,
    )
    return resp.content[0].text, None


def _openai(model, messages, api_key, system, temperature, max_tokens, top_p):
    import openai
    client = openai.OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    return resp.choices[0].message.content, None


def _gemini(model, messages, api_key, system, temperature, max_tokens, top_p, top_k):
    import requests
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload: dict = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {
            "temperature":    temperature,
            "maxOutputTokens": max_tokens,
            "topP":           top_p,
        },
    }
    if top_k > 0:
        payload["generationConfig"]["topK"] = top_k
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    candidates = r.json().get("candidates", [])
    if not candidates:
        return None, "No candidates returned"
    return candidates[0]["content"]["parts"][0]["text"], None


def _mistral(model, messages, api_key, system, temperature, max_tokens, top_p):
    import requests
    r = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model":       model,
            "messages":    [{"role": "system", "content": system}] + messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "top_p":       top_p,
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"], None


def _openrouter(model, messages, api_key, system, temperature, max_tokens, top_p):
    import requests
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model":       model,
            "messages":    [{"role": "system", "content": system}] + messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "top_p":       top_p,
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"], None
