"""
app/core/session_auth.py — HMAC-signed session key generation and validation.
Prevents anonymous/forged session_key abuse on the chat endpoint.
Sessions are keyed as: {prefix}:{random_hex}:{hmac_signature}
No database required — signature is self-contained.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, status

from app.core.config import settings


_SEP = ":"
_VERSION = "v1"


def generate_session_key(prefix: str = "ses") -> str:
    """
    Generate a cryptographically signed session key.
    Format: v1:{prefix}:{random_hex_16}:{timestamp}:{hmac_signature}

    The client receives this key and must use it as-is.
    Server validates the HMAC on every chat request.
    """
    random_part = secrets.token_hex(16)
    ts = str(int(time.time()))
    payload = f"{_VERSION}{_SEP}{prefix}{_SEP}{random_part}{_SEP}{ts}"
    sig = _sign(payload)
    return f"{payload}{_SEP}{sig}"


def validate_session_key(session_key: str) -> str:
    """
    Validate a signed session key.
    Returns the validated session_key on success.
    Raises HTTP 401 if the key is missing, malformed, or tampered.
    """
    if not session_key or not session_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session_key. Call /api/chat/session to get one.",
        )

    parts = session_key.split(_SEP)

    # Minimum required parts: version, prefix, random, timestamp, signature
    if len(parts) < 5:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session_key format.",
        )

    # Reconstruct payload (all parts except last) and provided signature
    provided_sig = parts[-1]
    payload = _SEP.join(parts[:-1])

    expected_sig = _sign(payload)
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or tampered session_key.",
        )

    return session_key


def _sign(payload: str) -> str:
    """Generate HMAC-SHA256 signature of payload using SECRET_KEY."""
    h = hmac.new(
        key=settings.SECRET_KEY.encode(),
        msg=payload.encode(),
        digestmod=hashlib.sha256,
    )
    return h.hexdigest()
