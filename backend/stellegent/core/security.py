"""JWT issue/decode (framework-agnostic)."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from ..config import JWT_SECRET, JWT_EXPIRY_MIN


def _issue(payload: dict, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    full_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(full_payload, JWT_SECRET, algorithm="HS256")


def issue_token(user_id: int, username: str, role: str) -> str:
    return _issue({
        "purpose": "session",
        "sub": str(user_id),
        "uid": int(user_id),
        "username": username,
        "role": role,
    }, JWT_EXPIRY_MIN)


def issue_mfa_token(user_id: int, username: str, role: str) -> str:
    return _issue({
        "purpose": "mfa",
        "sub": str(user_id),
        "uid": int(user_id),
        "username": username,
        "role": role,
    }, 10)


def issue_oauth_state(*, mode: str, next_path: str, nonce: str,
                      redirect_uri: str) -> str:
    return _issue({
        "purpose": "google_oauth_state",
        "sub": "google",
        "mode": mode,
        "next": next_path,
        "nonce": nonce,
        # Pin the exact redirect_uri sent at authorize time so the token
        # exchange uses a byte-identical value (Google requires exact match).
        "redirect_uri": redirect_uri,
    }, 10)


def decode_token(token: str, *, purpose: str = "session") -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    # Pre-upgrade session tokens did not carry a purpose claim.
    token_purpose = payload.get("purpose", "session")
    if token_purpose != purpose:
        return None
    return payload
