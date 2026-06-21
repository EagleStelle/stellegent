"""Auth routes: login, register, logout, me, password reset (local accounts).

Google OAuth columns exist in the schema but SSO is not wired up here yet; only
local email+password auth is implemented. Tokens are returned in the body (for
Bearer clients) and set as an httponly cookie (for the SPA).
"""
from __future__ import annotations
import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ...core.security import issue_token
from ...config import JWT_EXPIRY_MIN
from ...db import (verify_user_by_email, create_user, get_user_by_id, get_user_by_email,
                   create_reset_token, consume_reset_token, set_password)
from ...deps import current_user, log_action
from ...schemas import (LoginRequest, RegisterRequest, TokenResponse, UserOut,
                        ForgotPasswordRequest, ResetPasswordRequest,
                        MessageResponse)

log = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

_COOKIE_MAX_AGE = JWT_EXPIRY_MIN * 60


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie("token", token, httponly=True, samesite="lax",
                    max_age=_COOKIE_MAX_AGE)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response):
    user = verify_user_by_email(str(body.email), body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    if user["disabled"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
    token = issue_token(user["id"], user["username"], user["role"])
    _set_cookie(response, token)
    return TokenResponse(token=token, role=user["role"], username=user["username"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, response: Response):
    if get_user_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    try:
        uid = create_user(body.username, body.password, role="student",
                          email=body.email)
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "account exists")
    token = issue_token(uid, body.username, "student")
    _set_cookie(response, token)
    return TokenResponse(token=token, role="student", username=body.username)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie("token")
    return MessageResponse(ok=True)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    row = get_user_by_id(user["uid"])
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return UserOut(uid=row["id"], username=row["username"], role=row["role"],
                   email=row["email"])


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest):
    """Always returns ok (no account enumeration). With no SMTP configured the
    reset token is returned in the response for development use."""
    user = get_user_by_email(body.email)
    if not user:
        return MessageResponse(ok=True, message="if the email exists, a reset link was sent")
    token = create_reset_token(user["id"])
    # TODO: send via SMTP when configured. For now surface token for dev.
    return MessageResponse(ok=True, message="reset token generated", reset_token=token)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest):
    uid = consume_reset_token(body.token)
    if uid is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    set_password(uid, body.password)
    return MessageResponse(ok=True, message="password updated")
