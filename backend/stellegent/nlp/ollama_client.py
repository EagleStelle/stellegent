"""Thin Ollama HTTP client."""
from __future__ import annotations

import logging
import threading
from typing import List, Optional

import requests

from ..config import (
    OLLAMA_AUTO_PULL,
    OLLAMA_HOST,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_PULL_TIMEOUT,
    OLLAMA_REQUEST_TIMEOUT,
)

log = logging.getLogger(__name__)
_ensure_lock = threading.Lock()
_ensured_models: set[tuple[str, str]] = set()


def _base_url(host: Optional[str] = None) -> str:
    return (host or OLLAMA_HOST).rstrip("/")


def _model_key(host: Optional[str], model: str) -> tuple[str, str]:
    return (_base_url(host), model)


def _installed_model_names(payload: dict) -> set[str]:
    names: set[str] = set()
    for item in payload.get("models", []):
        if isinstance(item, dict):
            for key in ("name", "model"):
                value = item.get(key)
                if isinstance(value, str):
                    names.add(value)
    return names


def _model_installed(base_url: str, model: str, timeout: int) -> bool:
    r = requests.get(f"{base_url}/api/tags", timeout=min(timeout, 30))
    r.raise_for_status()
    return model in _installed_model_names(r.json())


def _pull_model(base_url: str, model: str, timeout: int) -> None:
    log.info("pulling Ollama model %s", model)
    r = requests.post(
        f"{base_url}/api/pull",
        json={"model": model, "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    payload = r.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise requests.exceptions.HTTPError(
            f"Ollama pull failed for {model}: {payload['error']}",
            response=r,
        )
    log.info("Ollama model %s is ready", model)


def ensure_model(model: Optional[str] = None, host: Optional[str] = None,
                 timeout: Optional[int] = None, force: bool = False) -> None:
    if not OLLAMA_AUTO_PULL:
        return
    target_model = model or OLLAMA_MODEL
    pull_timeout = timeout or OLLAMA_PULL_TIMEOUT
    key = _model_key(host, target_model)
    if not force and key in _ensured_models:
        return
    with _ensure_lock:
        if not force and key in _ensured_models:
            return
        base_url = key[0]
        if not _model_installed(base_url, target_model, pull_timeout):
            _pull_model(base_url, target_model, pull_timeout)
        _ensured_models.add(key)


def _post_with_model(endpoint: str, payload: dict, model: str,
                     host: Optional[str], timeout: int) -> requests.Response:
    ensure_model(model, host=host)
    url = _base_url(host) + endpoint
    r = requests.post(url, json=payload, timeout=timeout)
    if r.status_code == 404 and OLLAMA_AUTO_PULL:
        _ensured_models.discard(_model_key(host, model))
        ensure_model(model, host=host, force=True)
        r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r


def _options(defaults: dict, options: Optional[dict]) -> dict:
    merged = {"num_ctx": OLLAMA_NUM_CTX, **defaults}
    if options:
        merged.update(options)
    return merged


def _with_keep_alive(payload: dict) -> dict:
    if OLLAMA_KEEP_ALIVE:
        payload["keep_alive"] = OLLAMA_KEEP_ALIVE
    return payload


def generate(prompt: str, model: Optional[str] = None,
             host: Optional[str] = None, timeout: int = OLLAMA_REQUEST_TIMEOUT,
             options: Optional[dict] = None) -> str:
    target_model = model or OLLAMA_MODEL
    payload = _with_keep_alive({
        "model": target_model,
        "prompt": prompt,
        "stream": False,
        "options": _options({"temperature": 0.2}, options),
    })
    r = _post_with_model("/api/generate", payload, target_model, host, timeout)
    return r.json().get("response", "").strip()


def chat(messages: List[dict], model: Optional[str] = None,
         host: Optional[str] = None, timeout: int = OLLAMA_REQUEST_TIMEOUT,
         options: Optional[dict] = None) -> str:
    target_model = model or OLLAMA_MODEL
    payload = _with_keep_alive({
        "model": target_model,
        "messages": messages,
        "stream": False,
        "options": _options({"temperature": 0.0}, options),
    })
    r = _post_with_model("/api/chat", payload, target_model, host, timeout)
    return r.json().get("message", {}).get("content", "").strip()
