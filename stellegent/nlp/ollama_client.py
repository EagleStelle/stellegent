"""Thin Ollama HTTP client."""
from __future__ import annotations
from typing import List, Optional
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


def chat(messages: List[dict], model: Optional[str] = None,
         host: Optional[str] = None, timeout: int = 120,
         options: Optional[dict] = None) -> str:
    """Chat endpoint — uses model's instruct template, avoids prompt echo."""
    url = (host or OLLAMA_HOST).rstrip("/") + "/api/chat"
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": options or {"temperature": 0.0, "num_ctx": 4096},
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()
