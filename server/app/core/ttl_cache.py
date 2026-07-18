"""
app/core/ttl_cache.py — Tiny in-process TTL cache for hot read endpoints.
Keeps catalog/orders responses warm so UI does not wait on Supabase every time.
"""
from __future__ import annotations

import time
from typing import Any, Optional

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Optional[Any]:
    hit = _store.get(key)
    if not hit:
        return None
    expires, value = hit
    if expires < time.monotonic():
        _store.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl_seconds: float = 45.0) -> None:
    _store[key] = (time.monotonic() + ttl_seconds, value)


def invalidate(prefix: str = "") -> None:
    if not prefix:
        _store.clear()
        return
    for key in list(_store.keys()):
        if key.startswith(prefix):
            _store.pop(key, None)
