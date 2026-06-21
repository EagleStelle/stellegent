"""TOTP helpers for authenticator apps.

The implementation follows RFC 6238 so it works with Google Authenticator,
1Password, Authy, Microsoft Authenticator, and other standard TOTP apps.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import struct
import time
from io import BytesIO
from typing import Optional
from urllib.parse import quote, urlencode


TOTP_DIGITS = 6
TOTP_PERIOD = 30
RECOVERY_CODE_COUNT = 8
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_totp_secret() -> str:
    """Return a Google Authenticator-compatible base32 secret."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    compact = secret.replace(" ", "").upper()
    padding = "=" * ((8 - len(compact) % 8) % 8)
    return base64.b32decode(compact + padding, casefold=True)


def totp_code(secret: str, *, for_time: Optional[int] = None) -> str:
    counter = int((for_time if for_time is not None else time.time()) // TOTP_PERIOD)
    key = _decode_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, *, window: int = 1) -> bool:
    clean = "".join(ch for ch in str(code) if ch.isdigit())
    if len(clean) != TOTP_DIGITS:
        return False
    now = int(time.time())
    try:
        for step in range(-window, window + 1):
            candidate = totp_code(secret, for_time=now + (step * TOTP_PERIOD))
            if hmac.compare_digest(candidate, clean):
                return True
    except (binascii.Error, ValueError):
        return False
    return False


def build_otpauth_uri(*, issuer: str, account: str, secret: str) -> str:
    label = f"{issuer}:{account}"
    query = urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": str(TOTP_DIGITS),
        "period": str(TOTP_PERIOD),
    })
    return f"otpauth://totp/{quote(label)}?{query}"


def qr_png_data_url(value: str) -> Optional[str]:
    try:
        import qrcode
    except ImportError:
        return None

    image = qrcode.make(value)
    buf = BytesIO()
    image.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())
