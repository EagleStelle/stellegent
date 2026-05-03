"""Thin Ollama HTTP client. No deps beyond requests."""
from __future__ import annotations
import json
from typing import Optional
import requests

from ..config import OLLAMA_HOST, OLLAMA_MODEL


def generate(prompt: str, model: Optional[str] = None,
             host: Optional[str] = None, timeout: int = 120,
             options: Optional[dict] = None) -> str:
    url = (host or OLLAMA_HOST).rstrip("/") + "/api/generate"
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": options or {"temperature": 0.2, "num_ctx": 4096},
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def is_available(host: Optional[str] = None, timeout: int = 3) -> bool:
    url = (host or OLLAMA_HOST).rstrip("/") + "/api/tags"
    try:
        return requests.get(url, timeout=timeout).ok
    except Exception:
        return False
