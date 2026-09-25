"""Unified chat() helper with an automatic fallback chain: Ollama Cloud ->
Groq -> OpenRouter. Reads API keys from settings.config (one directory above
this project, per the repo README), falling back to environment variables
of the same name so keys can also be injected via the shell/CI.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import requests

from src.common import paths


class LLMUnavailableError(RuntimeError):
    """Raised when no configured LLM provider could serve the request."""


def _parse_settings_config(path: Path) -> dict:
    values: dict = {}
    if not path.exists():
        return values
    pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]?([^'\"\n]*)['\"]?\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


_SETTINGS_CONFIG_PATH = Path(
    os.environ.get("SETTINGS_CONFIG_PATH", str(paths.PROJECT_ROOT.parent / "settings.config"))
)
_SETTINGS = _parse_settings_config(_SETTINGS_CONFIG_PATH)


def _get_key(name: str):
    return os.environ.get(name) or _SETTINGS.get(name)


OLLAMA_API_KEY = _get_key("OLLAMA_API_KEY")
GROQ_API_KEY = _get_key("GROQ_API_KEY")
OPENROUTER_API_KEY = _get_key("OPENROUTER_API_KEY")

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b-cloud")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

_REQUEST_TIMEOUT = 30


def _chat_ollama_cloud(system: str, user: str) -> str:
    if not OLLAMA_API_KEY:
        raise LLMUnavailableError("OLLAMA_API_KEY not configured")
    response = requests.post(
        "https://ollama.com/api/chat",
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def _chat_openai_compatible(url: str, api_key, model: str, system: str, user: str) -> str:
    if not api_key:
        raise LLMUnavailableError(f"no API key configured for {url}")
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _chat_groq(system: str, user: str) -> str:
    return _chat_openai_compatible(
        "https://api.groq.com/openai/v1/chat/completions", GROQ_API_KEY, GROQ_MODEL, system, user
    )


def _chat_openrouter(system: str, user: str) -> str:
    return _chat_openai_compatible(
        "https://openrouter.ai/api/v1/chat/completions", OPENROUTER_API_KEY, OPENROUTER_MODEL, system, user
    )


_PROVIDER_CHAIN = [
    ("ollama_cloud", _chat_ollama_cloud),
    ("groq", _chat_groq),
    ("openrouter", _chat_openrouter),
]


def chat(user: str, system: str = "You are a helpful assistant."):
    """Try each provider in order. Returns (content, provider_name)."""
    errors = []
    for name, fn in _PROVIDER_CHAIN:
        try:
            return fn(system, user), name
        except Exception as exc:  # broad on purpose: any provider failure should fall through
            errors.append(f"{name}: {exc}")
    raise LLMUnavailableError("All LLM providers failed: " + " | ".join(errors))
