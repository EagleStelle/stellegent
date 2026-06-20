"""FastAPI dependencies: auth (current user / role gate) + request audit."""
from __future__ import annotations
from typing import Optional, Sequence

from fastapi import Depends, HTTPException, Request, status

from .core.security import decode_token
from .db import audit


def _token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")


def current_user(request: Request) -> dict:
    tok = _token_from_request(request)
    data = decode_token(tok) if tok else None
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return data


def require_roles(*roles: str):
    """Dependency factory: 403 unless the user's role is in ``roles``."""
    allowed: Sequence[str] = roles

    def _dep(user: dict = Depends(current_user)) -> dict:
        if allowed and user.get("role") not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return user

    return _dep


def log_action(request: Request, user: Optional[dict], action: str,
               target_id: Optional[str] = None) -> None:
    uid = user.get("uid") if user else None
    ip = request.client.host if request.client else None
    audit(uid, action, target_id, ip)
