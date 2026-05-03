"""JWT auth helpers."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Sequence

import jwt
from flask import request, jsonify, g, redirect, url_for

from ..config import JWT_SECRET, JWT_EXPIRY_MIN
from ..db import get_user, audit


def issue_token(user_id: int, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "uid": int(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRY_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def _get_token_from_request() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")


def login_required(roles: Optional[Sequence[str]] = None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            tok = _get_token_from_request()
            data = decode_token(tok) if tok else None
            if not data:
                if request.path.startswith("/api"):
                    return jsonify({"error": "unauthorized"}), 401
                return redirect(url_for("auth.login_page"))
            if roles and data.get("role") not in roles:
                return jsonify({"error": "forbidden"}), 403
            g.user = data
            return fn(*a, **kw)
        return wrapper
    return deco


def log_action(action: str, target_id: Optional[str] = None) -> None:
    user = getattr(g, "user", None)
    uid = user.get("uid") if user else None
    audit(uid, action, target_id, request.remote_addr)
