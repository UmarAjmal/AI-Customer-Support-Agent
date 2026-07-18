"""
app/core/rate_limiter.py — In-process sliding window rate limiter.
No external Redis needed. Works per-IP with configurable window and max requests.
Thread-safe for async environments (asyncio single-threaded event loop).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request, HTTPException, status


# ── Store: ip → deque of timestamps within the window ────────────────────────
_request_log: dict[str, deque] = defaultdict(deque)


def _get_client_ip(request: Request) -> str:
    """
    Extract real client IP — handles Render/Nginx reverse proxy via X-Forwarded-For.
    Falls back to direct connection IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For: client, proxy1, proxy2 — take first
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    request: Request,
    max_requests: int = 20,
    window_seconds: int = 60,
    endpoint_label: str = "chat",
) -> None:
    """
    FastAPI dependency: raises HTTP 429 if caller exceeds rate limit.
    Uses sliding window algorithm — more accurate than fixed-window counters.

    Args:
        request:         FastAPI Request object (injected via Depends)
        max_requests:    Maximum allowed requests within the window
        window_seconds:  Time window in seconds (default: 60s)
        endpoint_label:  Used for namespacing keys (prevents collisions across routes)

    Usage:
        @router.post("/stream")
        async def chat(req: ..., _: None = Depends(chat_rate_limit)):
            ...
    """
    ip = _get_client_ip(request)
    key = f"{endpoint_label}:{ip}"
    now = time.monotonic()
    window_start = now - window_seconds

    q = _request_log[key]

    # Evict timestamps outside the sliding window
    while q and q[0] < window_start:
        q.popleft()

    if len(q) >= max_requests:
        retry_after = int(window_seconds - (now - q[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {max_requests} requests per {window_seconds}s. "
                f"Please wait {retry_after} seconds before trying again."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    q.append(now)


def make_rate_limit_dep(max_requests: int = 20, window_seconds: int = 60, label: str = "api"):
    """
    Factory function to create a FastAPI dependency with custom limits.

    Example:
        chat_rate_limit = make_rate_limit_dep(max_requests=20, window_seconds=60, label="chat")

        @router.post("/stream")
        async def endpoint(req, _=Depends(chat_rate_limit)):
            ...
    """
    def _dep(request: Request) -> None:
        check_rate_limit(request, max_requests=max_requests, window_seconds=window_seconds, endpoint_label=label)
    return _dep
