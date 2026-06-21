"""In-process sliding-window rate limiting.

Sized for the single-worker deployment this app runs as (one uvicorn process,
SQLite). State is per-process and resets on restart; that is acceptable for the
abuse this guards against (email send spam), where a hard durable counter is not
required. Swap for a shared store (Redis) if the app is ever scaled out.
"""
from __future__ import annotations

import threading
import time
from typing import Iterable

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def allow(key: str, *, limit: int, window_s: float) -> bool:
    """Return True (and record the event) if `key` is under `limit` within `window_s`.

    Throttled calls are *not* recorded, so being blocked does not extend the
    caller's own cooldown.
    """
    now = time.monotonic()
    cutoff = now - window_s
    with _lock:
        hits = [t for t in _hits.get(key, ()) if t > cutoff]
        if len(hits) >= limit:
            _hits[key] = hits
            return False
        hits.append(now)
        _hits[key] = hits
        return True


def allow_many(rules: Iterable[tuple[str, int, float]]) -> bool:
    """Atomically record a hit for every rule if all rules are under limit."""
    rule_list = list(rules)
    now = time.monotonic()
    with _lock:
        pruned: dict[str, list[float]] = {}
        for key, _limit, window_s in rule_list:
            cutoff = now - window_s
            pruned[key] = [t for t in _hits.get(key, ()) if t > cutoff]

        if any(len(pruned[key]) >= limit for key, limit, _window_s in rule_list):
            _hits.update(pruned)
            return False

        for key, _limit, _window_s in rule_list:
            pruned[key].append(now)
        _hits.update(pruned)
        return True


def reset(key: str | None = None) -> None:
    """Clear limiter state (all keys, or one). Intended for tests."""
    with _lock:
        if key is None:
            _hits.clear()
        else:
            _hits.pop(key, None)
