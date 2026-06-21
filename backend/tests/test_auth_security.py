import stellegent.config as cfg
from fastapi.testclient import TestClient

from stellegent.core import ratelimit
from stellegent.core import email as email_core
from stellegent.core.mfa import (
    generate_recovery_codes,
    generate_totp_secret,
    normalize_recovery_code,
    totp_code,
    verify_totp,
)


def test_totp_roundtrip():
    secret = generate_totp_secret()
    code = totp_code(secret)
    assert verify_totp(secret, code)
    assert not verify_totp(secret, "000000" if code != "000000" else "111111")


def test_account_security_store(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "auth.db")
    from stellegent import db

    db.init_db()
    uid = db.create_user("Ada Lovelace", "secret123", "student", email="ada@example.com")

    secret = generate_totp_secret()
    db.set_totp_secret(uid, secret)
    db.enable_totp(uid)
    codes = generate_recovery_codes()
    normalized = [normalize_recovery_code(c) for c in codes]
    db.replace_recovery_codes(uid, normalized)

    summary = db.account_security_summary(uid)
    assert summary["two_factor_enabled"] is True
    assert summary["google_linked"] is False
    assert summary["has_password"] is True
    assert db.consume_recovery_code(uid, normalized[0])
    assert not db.consume_recovery_code(uid, normalized[0])

    db.link_google_account(uid, google_sub="google-sub-1", email_verified=True)
    assert db.get_user_by_google_sub("google-sub-1")["id"] == uid
    assert db.account_security_summary(uid)["google_linked"] is True

    db.unlink_google_account(uid)
    assert db.get_user_by_google_sub("google-sub-1") is None


def test_email_verification_token(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "email.db")
    from stellegent import db

    db.init_db()
    uid = db.create_user("Grace Hopper", "secret123", "student", email="grace@example.com")
    token = db.create_email_verification_token(uid)
    assert db.consume_email_verification_token(token) == uid
    assert db.account_security_summary(uid)["email_verified"] == 1
    assert db.consume_email_verification_token(token) is None


def test_multiple_email_verification_tokens_remain_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "email-multiple.db")
    from stellegent import db

    db.init_db()
    uid = db.create_user("Grace Hopper", "secret123", "student", email="grace@example.com")
    first_token = db.create_email_verification_token(uid)
    second_token = db.create_email_verification_token(uid)

    assert db.consume_email_verification_token(first_token) == uid
    assert db.consume_email_verification_token(second_token) == uid


def test_email_verification_link_route(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "email-route.db")
    from stellegent import db
    from stellegent.main import create_app

    db.init_db()
    uid = db.create_user("Grace Hopper", "secret123", "student", email="grace@example.com")
    token = db.create_email_verification_token(uid)

    with TestClient(create_app()) as client:
        response = client.get(
            f"/api/v1/verify-email?token={token}",
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/verify-email?verified=1"
    assert db.account_security_summary(uid)["email_verified"] == 1


def test_verification_email_send_is_rate_limited(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "email-rate.db")
    monkeypatch.setattr(email_core.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(
        email_core.settings,
        "resend_from_email",
        "Stellegent <noreply@example.com>",
    )
    ratelimit.reset()
    from stellegent import db
    from stellegent.api.v1 import auth
    from stellegent.main import create_app

    sent = []

    def fake_send_email_verification(*, to, verify_url):
        sent.append((to, verify_url))
        return email_core.EmailSendResult(sent=True, message_id="email_123")

    monkeypatch.setattr(auth, "send_email_verification", fake_send_email_verification)

    db.init_db()
    db.create_user("Grace Hopper", "secret123", "student", email="grace@example.com")

    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/login",
            json={"email": "grace@example.com", "password": "secret123"},
        )
        assert login.status_code == 200

        for _ in range(3):
            response = client.post("/api/v1/account/email/verification")
            assert response.status_code == 200

        response = client.post("/api/v1/account/email/verification")

    assert response.status_code == 429
    assert response.json()["detail"] == "too many email requests; please wait before trying again"
    assert len(sent) == 3
    assert all("/api/v1/verify-email?token=" in verify_url for _to, verify_url in sent)
    ratelimit.reset()


def test_password_reset_email_send_is_rate_limited_without_enumeration(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "reset-rate.db")
    monkeypatch.setattr(email_core.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(
        email_core.settings,
        "resend_from_email",
        "Stellegent <noreply@example.com>",
    )
    ratelimit.reset()
    from stellegent import db
    from stellegent.api.v1 import auth
    from stellegent.main import create_app

    sent = []

    def fake_send_password_reset_email(*, to, reset_url):
        sent.append((to, reset_url))
        return email_core.EmailSendResult(sent=True, message_id="email_123")

    monkeypatch.setattr(auth, "send_password_reset_email", fake_send_password_reset_email)

    db.init_db()
    db.create_user("Grace Hopper", "secret123", "student", email="grace@example.com")

    with TestClient(create_app()) as client:
        for _ in range(3):
            response = client.post(
                "/api/v1/forgot-password",
                json={"email": "grace@example.com"},
            )
            assert response.status_code == 200
            assert response.json()["message"] == "Reset link sent."

        limited = client.post(
            "/api/v1/forgot-password",
            json={"email": "grace@example.com"},
        )
        unknown = client.post(
            "/api/v1/forgot-password",
            json={"email": "unknown@example.com"},
        )

    assert limited.status_code == 200
    assert unknown.status_code == 200
    assert limited.json()["message"] == "Reset link sent."
    assert unknown.json()["message"] == "Reset link sent."
    assert len(sent) == 3
    ratelimit.reset()


def test_resend_payload(monkeypatch):
    sent = {}

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"id": "email_123"}

        def raise_for_status(self):
            raise AssertionError("should not raise")

    def fake_post(url, *, json, headers, timeout):
        sent["url"] = url
        sent["json"] = json
        sent["headers"] = headers
        sent["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(email_core.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(email_core.settings, "resend_from_email", "Stellegent <noreply@example.com>")
    monkeypatch.setattr(email_core.requests, "post", fake_post)

    result = email_core.send_password_reset_email(
        to="ada@example.com",
        reset_url="https://example.com/reset?token=abc",
    )

    assert result.message_id == "email_123"
    assert sent["url"] == "https://api.resend.com/emails"
    assert sent["json"]["to"] == ["ada@example.com"]
    assert sent["json"]["from"] == "Stellegent <noreply@example.com>"
    assert sent["json"]["subject"] == "Reset your Stellegent password"
    assert sent["headers"]["Authorization"] == "Bearer re_test"
    assert sent["headers"]["User-Agent"].startswith("Stellegent/")
