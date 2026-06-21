"""Admin-only account management."""
from __future__ import annotations
import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...db import create_user, delete_user, list_users, update_user
from ...deps import require_roles, log_action
from ...schemas import (
    ManagedUserCreate, ManagedUserOut, ManagedUserUpdate, MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[ManagedUserOut])
def users(_u: dict = Depends(require_roles("admin"))):
    return [dict(r) for r in list_users()]


@router.post("/users", response_model=ManagedUserOut, status_code=201)
def create_managed_user(body: ManagedUserCreate, request: Request,
                        user: dict = Depends(require_roles("admin"))):
    try:
        uid = create_user(body.username, body.password, body.role,
                          email=str(body.email))
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "account exists")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    log_action(request, user, "create_user", str(uid))
    return dict(next(r for r in list_users() if r["id"] == uid))


@router.patch("/users/{user_id}", response_model=ManagedUserOut)
def update_managed_user(user_id: int, body: ManagedUserUpdate,
                        request: Request,
                        user: dict = Depends(require_roles("admin"))):
    kwargs = {}
    fields = body.model_fields_set
    if "username" in fields:
        kwargs["username"] = body.username
    if "email" in fields and body.email is not None:
        kwargs["email"] = str(body.email)
    if "role" in fields:
        kwargs["role"] = body.role
    if "password" in fields:
        kwargs["password"] = body.password
    if "disabled" in fields:
        kwargs["disabled"] = body.disabled
    try:
        row = update_user(user_id, **kwargs)
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "account exists")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    log_action(request, user, "update_user", str(user_id))
    return dict(row)


@router.delete("/users/{user_id}", response_model=MessageResponse)
def remove_managed_user(user_id: int, request: Request,
                        user: dict = Depends(require_roles("admin"))):
    try:
        deleted = delete_user(user_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    log_action(request, user, "delete_user", str(user_id))
    return MessageResponse(ok=True)
