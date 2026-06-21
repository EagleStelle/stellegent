"""Auth routes: local auth, account settings, TOTP MFA, and Google OAuth."""
from __future__ import annotations
import hmac
import logging
import secrets
import sqlite3
from urllib.parse import urlencode, urlparse

import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from ...core.email import (
    EmailNotConfigured, email_configured, send_email_verification,
    send_password_reset_email,
)
from ...core.mfa import (
    build_otpauth_uri, generate_recovery_codes, generate_totp_secret,
    normalize_recovery_code, qr_png_data_url, verify_totp,
)
from ...core.security import (
    decode_token, issue_mfa_token, issue_oauth_state, issue_token,
)
from ...config import JWT_EXPIRY_MIN, settings
from ...db import (
    account_security_summary, consume_recovery_code, consume_reset_token,
    consume_email_verification_token, create_email_verification_token,
    create_google_user, create_reset_token, create_user, disable_totp, enable_totp,
    get_user_by_email, get_user_by_google_sub, get_user_by_id,
    link_google_account, replace_recovery_codes, set_password,
    set_totp_secret, unlink_google_account, update_account_profile,
    verify_user_by_email, verify_user_password,
)
from ...deps import current_user, log_action
from ...schemas import (
    AccountOut, AccountUpdateRequest, ForgotPasswordRequest, LoginMfaRequest,
    LoginRequest, MessageResponse, MfaChallengeResponse, PasswordChangeRequest,
    RegisterRequest, ResetPasswordRequest, TokenResponse, TotpDisableRequest,
    TotpEnableResponse, TotpSetupResponse, TotpVerifyRequest, UserOut,
    VerifyEmailRequest,
)

log = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

_COOKIE_MAX_AGE = JWT_EXPIRY_MIN * 60
_MFA_COOKIE_MAX_AGE = 10 * 60
_OAUTH_COOKIE_MAX_AGE = 10 * 60
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"


def _is_https_request(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    return request.url.scheme == "https" or forwarded == "https"


def _cookie_secure(request: Request) -> bool:
    return settings.cookie_secure or _is_https_request(request)


def _set_cookie(resp: Response, request: Request, name: str, value: str,
                *, max_age: int) -> None:
    resp.set_cookie(
        name,
        value,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=_cookie_secure(request),
        max_age=max_age,
        path="/",
    )


def _delete_cookie(resp: Response, request: Request, name: str) -> None:
    resp.delete_cookie(
        name,
        path="/",
        samesite=settings.cookie_samesite,
        secure=_cookie_secure(request),
    )


def _set_session_cookie(resp: Response, request: Request, token: str) -> None:
    _set_cookie(resp, request, "token", token, max_age=_COOKIE_MAX_AGE)


def _set_mfa_cookie(resp: Response, request: Request, token: str) -> None:
    _set_cookie(resp, request, "mfa_token", token, max_age=_MFA_COOKIE_MAX_AGE)


def _set_oauth_state_cookie(resp: Response, request: Request, state: str) -> None:
    _set_cookie(resp, request, "oauth_state", state, max_age=_OAUTH_COOKIE_MAX_AGE)


def _token_response(row, request: Request, response: Response) -> TokenResponse:
    token = issue_token(row["id"], row["username"], row["role"])
    _set_session_cookie(response, request, token)
    return TokenResponse(token=token, role=row["role"], username=row["username"])


def _mfa_challenge(row, request: Request, response: Response) -> MfaChallengeResponse:
    token = issue_mfa_token(row["id"], row["username"], row["role"])
    _set_mfa_cookie(response, request, token)
    return MfaChallengeResponse(mfa_token=token)


def _verify_mfa_code(row, code: str) -> bool:
    if row["totp_secret"] and row["totp_enabled"]:
        if verify_totp(row["totp_secret"], code):
            return True
    recovery = normalize_recovery_code(code)
    if recovery and consume_recovery_code(row["id"], recovery):
        return True
    return False


def _safe_next(path: str | None, default: str) -> str:
    if not path or not path.startswith("/") or path.startswith("//"):
        return default
    if path.startswith("/api/"):
        return default
    return path


def _oauth_enabled() -> bool:
    return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)


def _request_origin(request: Request) -> str:
    allowed = {o.strip().rstrip("/") for o in settings.cors_origins.split(",") if o.strip()}
    for header in ("origin", "referer"):
        value = request.headers.get(header, "")
        if not value:
            continue
        parsed = urlparse(value)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else ""
        if parsed.scheme in {"http", "https"} and origin in allowed:
            return origin
    return ""


def _public_base(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    origin = _request_origin(request)
    if origin:
        return origin
    host = request.headers.get("host", "")
    if host:
        scheme = "https" if _is_https_request(request) else request.url.scheme
        return f"{scheme}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _google_redirect_uri(request: Request) -> str:
    if settings.google_oauth_redirect_uri:
        return settings.google_oauth_redirect_uri
    return f"{_public_base(request)}/api/v1/auth/google/callback"


def _app_url(request: Request, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{_public_base(request)}{path}"


def _maybe_current_user(request: Request) -> dict | None:
    try:
        return current_user(request)
    except HTTPException:
        return None


def _email_verified(claims: dict) -> bool:
    value = claims.get("email_verified")
    return value is True or str(value).lower() == "true"


def _check_google_domain(claims: dict) -> None:
    allowed = settings.google_allowed_domain.strip().lower()
    if not allowed:
        return
    email = str(claims.get("email", "")).lower()
    hosted_domain = str(claims.get("hd", "")).lower()
    if hosted_domain == allowed or email.endswith(f"@{allowed}"):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "google domain not allowed")


def _verify_google_id_token(id_token: str, nonce: str) -> dict:
    try:
        signing_key = jwt.PyJWKClient(_GOOGLE_JWKS_URL).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_oauth_client_id,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid google token") from exc
    if claims.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid google issuer")
    if claims.get("nonce") != nonce:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid google nonce")
    if not claims.get("sub") or not claims.get("email"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "incomplete google profile")
    _check_google_domain(claims)
    return claims


def _exchange_google_code(request: Request, code: str, nonce: str) -> dict:
    token_resp = requests.post(
        _GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": _google_redirect_uri(request),
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token_resp.status_code >= 400:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "google token exchange failed")
    id_token = token_resp.json().get("id_token")
    if not id_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "google id token missing")
    return _verify_google_id_token(id_token, nonce)


def _google_user(claims: dict):
    sub = str(claims["sub"])
    email = str(claims["email"])
    verified = _email_verified(claims)
    user = get_user_by_google_sub(sub)
    if user:
        return user
    if not verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "google email is not verified")
    existing = get_user_by_email(email)
    if existing:
        link_google_account(existing["id"], google_sub=sub, email_verified=True)
        return get_user_by_id(existing["id"])
    name = str(claims.get("name") or email.split("@", 1)[0])[:64]
    uid = create_google_user(
        username=name, email=email, google_sub=sub, email_verified=True,
    )
    return get_user_by_id(uid)


def _send_email_verification_for(row, request: Request) -> str:
    token = create_email_verification_token(row["id"])
    verify_url = _app_url(request, f"/verify-email?{urlencode({'token': token})}")
    send_email_verification(to=row["email"], verify_url=verify_url)
    return token


@router.post("/login", response_model=TokenResponse | MfaChallengeResponse)
def login(body: LoginRequest, request: Request, response: Response):
    user = verify_user_by_email(str(body.email), body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    if user["disabled"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
    if user["totp_enabled"]:
        return _mfa_challenge(user, request, response)
    return _token_response(user, request, response)


@router.post("/login/mfa", response_model=TokenResponse)
def login_mfa(body: LoginMfaRequest, request: Request, response: Response):
    token = body.mfa_token or request.cookies.get("mfa_token")
    data = decode_token(token, purpose="mfa") if token else None
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "verification expired")
    user = get_user_by_id(data["uid"])
    if not user or user["disabled"] or not user["totp_enabled"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    if not _verify_mfa_code(user, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid verification code")
    _delete_cookie(response, request, "mfa_token")
    return _token_response(user, request, response)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request, response: Response):
    if get_user_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    try:
        uid = create_user(body.username, body.password, role="student",
                          email=body.email)
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "account exists")
    row = get_user_by_id(uid)
    if row and email_configured():
        try:
            _send_email_verification_for(row, request)
        except Exception as exc:
            log.warning("verification email failed for user %s: %s", uid, exc)
    token = issue_token(uid, body.username, "student")
    _set_session_cookie(response, request, token)
    return TokenResponse(token=token, role="student", username=body.username)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response):
    _delete_cookie(response, request, "token")
    _delete_cookie(response, request, "mfa_token")
    return MessageResponse(ok=True)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    summary = account_security_summary(user["uid"])
    if not summary:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return UserOut(**summary)


@router.get("/account", response_model=AccountOut)
def account(user: dict = Depends(current_user)):
    summary = account_security_summary(user["uid"])
    if not summary:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return AccountOut(**summary)


@router.patch("/account", response_model=AccountOut)
def update_account(body: AccountUpdateRequest, request: Request,
                   user: dict = Depends(current_user)):
    try:
        row = update_account_profile(
            user["uid"], username=body.username.strip(), email=str(body.email),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not row["email_verified"] and email_configured():
        try:
            _send_email_verification_for(row, request)
        except Exception as exc:
            log.warning("verification email failed for user %s: %s", user["uid"], exc)
    log_action(request, user, "update_account", str(user["uid"]))
    return AccountOut(**account_security_summary(user["uid"]))


@router.post("/account/email/verification", response_model=MessageResponse)
def send_account_verification(request: Request, user: dict = Depends(current_user)):
    row = get_user_by_id(user["uid"])
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    if row["email_verified"]:
        return MessageResponse(ok=True, message="email already verified")
    try:
        token = _send_email_verification_for(row, request)
    except EmailNotConfigured:
        token = create_email_verification_token(row["id"])
        return MessageResponse(
            ok=True,
            message="verification token generated",
            verification_token=token,
        )
    except Exception as exc:
        log.warning("verification email failed for user %s: %s", user["uid"], exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "email delivery failed")
    return MessageResponse(ok=True, message="verification email sent")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(body: VerifyEmailRequest):
    uid = consume_email_verification_token(body.token)
    if uid is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    return MessageResponse(ok=True, message="email verified")


@router.post("/account/password", response_model=MessageResponse)
def change_password(body: PasswordChangeRequest, request: Request,
                    user: dict = Depends(current_user)):
    summary = account_security_summary(user["uid"])
    if not summary:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    if summary["has_password"] and not verify_user_password(
        user["uid"], body.current_password,
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is incorrect")
    set_password(user["uid"], body.new_password)
    log_action(request, user, "change_password", str(user["uid"]))
    return MessageResponse(ok=True, message="password updated")


@router.post("/account/2fa/setup", response_model=TotpSetupResponse)
def setup_totp(user: dict = Depends(current_user)):
    row = get_user_by_id(user["uid"])
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    secret = generate_totp_secret()
    set_totp_secret(user["uid"], secret)
    account_label = row["email"] or row["username"]
    uri = build_otpauth_uri(
        issuer=settings.app_name, account=account_label, secret=secret,
    )
    return TotpSetupResponse(
        secret=secret, otpauth_uri=uri, qr_data_url=qr_png_data_url(uri),
    )


@router.post("/account/2fa/enable", response_model=TotpEnableResponse)
def confirm_totp(body: TotpVerifyRequest, request: Request,
                 user: dict = Depends(current_user)):
    row = get_user_by_id(user["uid"])
    if not row or not row["totp_secret"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start setup first")
    if not verify_totp(row["totp_secret"], body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid verification code")
    enable_totp(user["uid"])
    recovery_codes = generate_recovery_codes()
    replace_recovery_codes(
        user["uid"], [normalize_recovery_code(c) for c in recovery_codes],
    )
    log_action(request, user, "enable_2fa", str(user["uid"]))
    return TotpEnableResponse(ok=True, recovery_codes=recovery_codes)


@router.post("/account/2fa/disable", response_model=MessageResponse)
def disable_totp_route(body: TotpDisableRequest, request: Request,
                       user: dict = Depends(current_user)):
    row = get_user_by_id(user["uid"])
    if not row or not row["totp_enabled"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2fa is not enabled")
    summary = account_security_summary(user["uid"])
    if summary and summary["has_password"]:
        if not body.current_password:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password required")
        if not verify_user_password(user["uid"], body.current_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is incorrect")
    if not _verify_mfa_code(row, body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid verification code")
    disable_totp(user["uid"])
    log_action(request, user, "disable_2fa", str(user["uid"]))
    return MessageResponse(ok=True, message="2fa disabled")


@router.post("/account/google/unlink", response_model=AccountOut)
def unlink_google(request: Request, user: dict = Depends(current_user)):
    try:
        row = unlink_google_account(user["uid"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    log_action(request, user, "unlink_google", str(user["uid"]))
    return AccountOut(**account_security_summary(user["uid"]))


@router.get("/auth/google/start")
def google_start(request: Request, mode: str = Query("login"),
                 next_path: str | None = Query(None, alias="next")):
    if not _oauth_enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "google oauth not configured")
    if mode not in {"login", "link"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid oauth mode")
    if mode == "link" and not _maybe_current_user(request):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")

    default_next = "/settings" if mode == "link" else "/courses"
    nonce = secrets.token_urlsafe(24)
    state = issue_oauth_state(
        mode=mode, next_path=_safe_next(next_path, default_next), nonce=nonce,
    )
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{_GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)
    _set_oauth_state_cookie(resp, request, state)
    return resp


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str | None = None,
                    state: str | None = None, error: str | None = None):
    cookie_state = request.cookies.get("oauth_state")
    state_payload = decode_token(state, purpose="google_oauth_state") if state else None
    mode = state_payload.get("mode") if state_payload else "login"
    default_next = "/settings" if mode == "link" else "/courses"
    next_path = _safe_next(state_payload.get("next") if state_payload else None,
                           default_next)

    def redirect(status_value: str) -> RedirectResponse:
        separator = "&" if "?" in next_path else "?"
        resp = RedirectResponse(f"{next_path}{separator}google={status_value}",
                                status_code=302)
        _delete_cookie(resp, request, "oauth_state")
        return resp

    if error:
        return redirect("cancelled")
    if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        return redirect("invalid_state")
    if not state_payload or not code:
        return redirect("invalid_state")

    try:
        claims = _exchange_google_code(request, code, state_payload["nonce"])
    except HTTPException as exc:
        log.warning("google oauth failed: %s", exc.detail)
        return redirect("failed")

    sub = str(claims["sub"])
    verified = _email_verified(claims)
    if mode == "link":
        current = _maybe_current_user(request)
        if not current:
            return redirect("login_required")
        existing = get_user_by_google_sub(sub)
        if existing and existing["id"] != current["uid"]:
            return redirect("conflict")
        link_google_account(current["uid"], google_sub=sub, email_verified=verified)
        return redirect("linked")

    try:
        user = _google_user(claims)
    except HTTPException as exc:
        log.warning("google login rejected: %s", exc.detail)
        return redirect("failed")
    if not user or user["disabled"]:
        return redirect("disabled")

    if user["totp_enabled"]:
        mfa_token = issue_mfa_token(user["id"], user["username"], user["role"])
        resp = RedirectResponse("/mfa?google=1", status_code=302)
        _delete_cookie(resp, request, "oauth_state")
        _set_mfa_cookie(resp, request, mfa_token)
        return resp

    token = issue_token(user["id"], user["username"], user["role"])
    resp = RedirectResponse(next_path, status_code=302)
    _delete_cookie(resp, request, "oauth_state")
    _set_session_cookie(resp, request, token)
    return resp


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Always returns ok to avoid account enumeration."""
    user = get_user_by_email(body.email)
    if not user:
        return MessageResponse(ok=True, message="if the email exists, a reset link was sent")
    token = create_reset_token(user["id"])
    reset_url = _app_url(request, f"/reset?{urlencode({'token': token})}")
    if not email_configured():
        return MessageResponse(ok=True, message="reset token generated", reset_token=token)
    try:
        send_password_reset_email(to=user["email"], reset_url=reset_url)
    except Exception as exc:
        log.warning("password reset email failed for user %s: %s", user["id"], exc)
    return MessageResponse(ok=True, message="if the email exists, a reset link was sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest):
    uid = consume_reset_token(body.token)
    if uid is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired token")
    set_password(uid, body.password)
    return MessageResponse(ok=True, message="password updated")
