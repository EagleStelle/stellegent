"""Transactional email delivery through Resend."""
from __future__ import annotations

import html
import logging
import secrets
from dataclasses import dataclass
from typing import Optional

import requests

from ..config import settings

log = logging.getLogger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


class EmailNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    message_id: Optional[str] = None


def email_configured() -> bool:
    return bool(settings.resend_api_key and settings.resend_from_email)


def _send_email(*, to: str, subject: str, html_body: str,
                text_body: str, tag: str) -> EmailSendResult:
    if not email_configured():
        raise EmailNotConfigured("Resend email is not configured")

    payload: dict[str, object] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
        "tags": [{"name": "kind", "value": tag}],
    }
    if settings.email_reply_to:
        payload["reply_to"] = settings.email_reply_to

    response = requests.post(
        _RESEND_EMAILS_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "User-Agent": f"{settings.app_name}/0.2.0",
            "Idempotency-Key": f"{tag}-{secrets.token_urlsafe(24)}",
        },
        timeout=10,
    )
    if response.status_code >= 400:
        log.warning("Resend email failed: %s %s", response.status_code, response.text)
        response.raise_for_status()
    data = response.json()
    return EmailSendResult(sent=True, message_id=data.get("id"))


def _button_html(label: str, url: str) -> str:
    safe_label = html.escape(label)
    safe_url = html.escape(url, quote=True)
    return (
        f'<a href="{safe_url}" '
        'style="display:inline-block;background:#E11D48;color:white;'
        'padding:10px 14px;border-radius:8px;text-decoration:none;'
        'font-weight:700">'
        f"{safe_label}</a>"
    )


def send_password_reset_email(*, to: str, reset_url: str) -> EmailSendResult:
    safe_url = html.escape(reset_url)
    html_body = (
        "<p>Use this link to reset your Stellegent password. "
        "It expires in 30 minutes.</p>"
        f"{_button_html('Reset password', reset_url)}"
        "<p>If the button does not work, paste this link into your browser:</p>"
        f"<p>{safe_url}</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )
    text_body = (
        "Use this link to reset your Stellegent password. "
        "It expires in 30 minutes.\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    return _send_email(
        to=to,
        subject="Reset your Stellegent password",
        html_body=html_body,
        text_body=text_body,
        tag="password_reset",
    )


def send_email_verification(*, to: str, verify_url: str) -> EmailSendResult:
    safe_url = html.escape(verify_url)
    html_body = (
        "<p>Confirm this email address for your Stellegent account. "
        "The link expires in 24 hours.</p>"
        f"{_button_html('Verify email', verify_url)}"
        "<p>If the button does not work, paste this link into your browser:</p>"
        f"<p>{safe_url}</p>"
    )
    text_body = (
        "Confirm this email address for your Stellegent account. "
        "The link expires in 24 hours.\n\n"
        f"{verify_url}"
    )
    return _send_email(
        to=to,
        subject="Verify your Stellegent email",
        html_body=html_body,
        text_body=text_body,
        tag="email_verify",
    )
