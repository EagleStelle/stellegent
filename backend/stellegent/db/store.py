"""SQLite store. Thread-safe via per-call connections. Schema via migrations."""
from __future__ import annotations
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import bcrypt

from .. import config as cfg
from .migrate import run_migrations

_VALID_ROLES = {"prof", "student", "admin"}
_VALID_VISIBILITY = {"public", "private"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_role(role: str) -> None:
    if role not in _VALID_ROLES:
        raise ValueError("invalid role")


def _validate_visibility(visibility: str) -> None:
    if visibility not in _VALID_VISIBILITY:
        raise ValueError("invalid visibility")


@contextmanager
def get_conn(db_path: Optional[Path] = None):
    p = Path(db_path or cfg.DB_PATH)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    with get_conn(db_path) as c:
        run_migrations(c)


# ---------- lectures ----------

def insert_lecture(*, lecture_id: str, date: str, course_name: Optional[str],
                   captured_at: str, image_path: str, docx_path: str,
                   pdf_path: str, txt_path: str, manifest_path: str,
                   raw_ocr_text: str, corrected_text: str, summary: str,
                   tags: Iterable[str], title: Optional[str] = None,
                   owner_user_id: Optional[int] = None,
                   visibility: str = "public",
                   course_id: Optional[int] = None,
                   raw_image_path: Optional[str] = None) -> None:
    _validate_visibility(visibility)
    with get_conn() as c:
        if course_id is not None and course_name is None:
            course = c.execute("SELECT name FROM courses WHERE id = ?",
                               (course_id,)).fetchone()
            if course:
                course_name = course["name"]
        c.execute("""
            INSERT OR REPLACE INTO lectures
            (id,date,course_name,title,captured_at,image_path,raw_image_path,
             docx_path,pdf_path,txt_path,manifest_path,raw_ocr_text,
             corrected_text,summary,tags,owner_user_id,visibility,course_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (lecture_id, date, course_name, title, captured_at, image_path,
              raw_image_path, docx_path, pdf_path, txt_path, manifest_path,
              raw_ocr_text, corrected_text, summary, json.dumps(list(tags)),
              owner_user_id, visibility, course_id))


def list_lectures(*, date: Optional[str] = None, course: Optional[str] = None,
                  q: Optional[str] = None, limit: int = 200,
                  user_id: Optional[int] = None,
                  role: Optional[str] = None) -> List[sqlite3.Row]:
    sql = """
        SELECT l.*, owner.username AS owner_username, c.name AS course_title, c.visibility AS course_visibility
        FROM lectures l
        LEFT JOIN users owner ON owner.id = l.owner_user_id
        LEFT JOIN courses c ON c.id = l.course_id
        WHERE 1=1
    """
    args: List = []
    if date:
        sql += " AND l.date = ?"
        args.append(date)
    if course:
        sql += " AND (l.course_name = ? OR c.name = ?)"
        args += [course, course]
    if q:
        sql += """
            AND (l.raw_ocr_text LIKE ? OR l.corrected_text LIKE ?
                 OR l.summary LIKE ? OR l.course_name LIKE ?
                 OR c.name LIKE ? OR owner.username LIKE ?)
        """
        like = f"%{q}%"
        args += [like, like, like, like, like, like]
    if role:
        _validate_role(role)
        if role == "prof":
            sql += """
                AND (
                    l.owner_user_id = ?
                    OR l.visibility = 'public'
                    OR EXISTS (
                        SELECT 1 FROM courses owned
                        WHERE owned.id = l.course_id
                          AND owned.faculty_id = ?
                    )
                )
            """
            args += [user_id, user_id]
        elif role == "student":
            sql += """
                AND (
                    l.visibility = 'public'
                    OR EXISTS (
                        SELECT 1 FROM lecture_students ls
                        WHERE ls.lecture_id = l.id
                          AND ls.user_id = ?
                    )
                    OR EXISTS (
                        SELECT 1 FROM course_students cs
                        WHERE cs.course_id = l.course_id
                          AND cs.user_id = ?
                    )
                )
            """
            args += [user_id, user_id]
    sql += " ORDER BY l.captured_at DESC LIMIT ?"
    args.append(limit)
    with get_conn() as c:
        return list(c.execute(sql, args))


def get_lecture(lecture_id: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("""
            SELECT l.*, owner.username AS owner_username, c.name AS course_title, c.visibility AS course_visibility
            FROM lectures l
            LEFT JOIN users owner ON owner.id = l.owner_user_id
            LEFT JOIN courses c ON c.id = l.course_id
            WHERE l.id = ?
        """, (lecture_id,)).fetchone()


def can_view_lecture(row: sqlite3.Row, *, user_id: int, role: str) -> bool:
    _validate_role(role)
    if role == "admin":
        return True
    if role == "prof":
        if row["owner_user_id"] == user_id:
            return True
        course_id = row["course_id"]
        if course_id is None:
            if row["visibility"] == "public":
                return True
            return False
        with get_conn() as c:
            is_faculty = c.execute(
                "SELECT 1 FROM courses WHERE id = ? AND faculty_id = ?",
                (course_id, user_id)).fetchone() is not None
            if is_faculty:
                return True
            
        if row["visibility"] == "public" and row["course_visibility"] == "public":
            return True
            
    if row["visibility"] == "public":
        return True
    with get_conn() as c:
        if c.execute(
            "SELECT 1 FROM lecture_students WHERE lecture_id = ? AND user_id = ?",
            (row["id"], user_id)).fetchone():
            return True
        return c.execute("""
            SELECT 1
            FROM course_students
            WHERE course_id = ?
              AND user_id = ?
        """, (row["course_id"], user_id)).fetchone() is not None


def can_manage_lecture(row: sqlite3.Row, *, user_id: int, role: str) -> bool:
    _validate_role(role)
    return role == "admin" or (role == "prof" and row["owner_user_id"] == user_id)


def update_lecture(lecture_id: str, **fields) -> Optional[sqlite3.Row]:
    allowed = {
        "course_name", "title", "summary", "corrected_text", "visibility",
        "owner_user_id", "course_id",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "visibility" in updates and updates["visibility"] is not None:
        _validate_visibility(updates["visibility"])
    if not updates:
        return get_lecture(lecture_id)
    if updates.get("course_id") is not None:
        with get_conn() as c:
            course = c.execute("SELECT name, faculty_id FROM courses WHERE id = ?",
                               (updates["course_id"],)).fetchone()
            if course:
                if "course_name" not in updates:
                    updates["course_name"] = course["name"]
                # A lecture is owned by the faculty of the course it sits on, so
                # moving it to another course transfers ownership accordingly.
                updates["owner_user_id"] = course["faculty_id"]
    parts = [f"{k} = ?" for k in updates]
    args = list(updates.values()) + [lecture_id]
    with get_conn() as c:
        c.execute(f"UPDATE lectures SET {', '.join(parts)} WHERE id = ?", args)
    return get_lecture(lecture_id)


def delete_lecture(lecture_id: str) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))


# ---------- users ----------

def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _merge_auth_provider(current: Optional[str], provider: str) -> str:
    parts = {p for p in (current or "").split("+") if p}
    parts.add(provider)
    if "local" in parts and "google" in parts:
        return "local+google"
    if "google" in parts:
        return "google"
    return "local"


def _has_password(row: sqlite3.Row) -> bool:
    return bool(row["password_hash"])


def admin_exists(exclude_user_id: Optional[int] = None) -> bool:
    sql = "SELECT 1 FROM users WHERE role = 'admin'"
    args: List = []
    if exclude_user_id is not None:
        sql += " AND id <> ?"
        args.append(exclude_user_id)
    with get_conn() as c:
        return c.execute(sql, args).fetchone() is not None


def create_user(username: str, password: str, role: str, email: str) -> int:
    _validate_role(role)
    if role == "admin" and admin_exists():
        raise ValueError("only one admin is allowed")
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (username,password_hash,role,email,auth_provider,"
            "email_verified,created_at) VALUES (?,?,?,?,'local',0,?)",
            (username, _hash_pw(password), role, email, _now()))
        return int(cur.lastrowid)


def create_google_user(*, username: str, email: str, google_sub: str,
                       email_verified: bool, role: str = "student") -> int:
    _validate_role(role)
    with get_conn() as c:
        cur = c.execute("""
            INSERT INTO users
            (username,password_hash,role,email,auth_provider,google_sub,
             email_verified,created_at,updated_at)
            VALUES (?, '', ?, ?, 'google', ?, ?, ?, ?)
        """, (
            username, role, email, google_sub, 1 if email_verified else 0,
            _now(), _now(),
        ))
        return int(cur.lastrowid)


def list_users(role: Optional[str] = None) -> List[sqlite3.Row]:
    sql = """
        SELECT id, username, email, role, auth_provider, email_verified,
               disabled, created_at, totp_enabled
        FROM users
        WHERE 1=1
    """
    args: List = []
    if role:
        _validate_role(role)
        sql += " AND role = ?"
        args.append(role)
    sql += """
        ORDER BY CASE role
            WHEN 'admin' THEN 0
            WHEN 'prof' THEN 1
            ELSE 2
        END, username COLLATE NOCASE
    """
    with get_conn() as c:
        return list(c.execute(sql, args))


def get_user(username: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()


def get_user_by_google_sub(google_sub: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE google_sub = ?",
            (google_sub,),
        ).fetchone()


def verify_user(username: str, password: str) -> Optional[sqlite3.Row]:
    u = get_user(username)
    if not u or not u["password_hash"]:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), u["password_hash"].encode("utf-8")):
        return u
    return None


def verify_user_by_email(email: str, password: str) -> Optional[sqlite3.Row]:
    u = get_user_by_email(email)
    if not u or not u["password_hash"]:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), u["password_hash"].encode("utf-8")):
        return u
    return None


def set_password(user_id: int, password: str) -> None:
    user = get_user_by_id(user_id)
    provider = _merge_auth_provider(user["auth_provider"] if user else None, "local")
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET password_hash = ?, auth_provider = ?, updated_at = ?
            WHERE id = ?
        """, (_hash_pw(password), provider, _now(), user_id))


def update_user(user_id: int, *, username: Optional[str] = None,
                email: Optional[str] = None, role: Optional[str] = None,
                password: Optional[str] = None,
                disabled: Optional[bool] = None) -> Optional[sqlite3.Row]:
    current = get_user_by_id(user_id)
    if not current:
        return None
    parts: List[str] = []
    args: List = []
    if username is not None:
        parts.append("username = ?")
        args.append(username)
    if email is not None:
        parts.append("email = ?")
        args.append(email)
        if email.lower() != str(current["email"]).lower():
            parts.append("email_verified = 0")
    if role is not None:
        _validate_role(role)
        if current["role"] == "admin" and role != "admin":
            raise ValueError("the admin account cannot be demoted")
        if role == "admin" and current["role"] != "admin":
            raise ValueError("only one admin is allowed")
        if role == "admin" and admin_exists(exclude_user_id=user_id):
            raise ValueError("only one admin is allowed")
        parts.append("role = ?")
        args.append(role)
    if password:
        parts.append("password_hash = ?")
        args.append(_hash_pw(password))
        parts.append("auth_provider = ?")
        args.append(_merge_auth_provider(current["auth_provider"], "local"))
    if disabled is not None:
        if current["role"] == "admin" and disabled:
            raise ValueError("the admin account cannot be disabled")
        parts.append("disabled = ?")
        args.append(1 if disabled else 0)
    if parts:
        parts.append("updated_at = ?")
        args.append(_now())
        args.append(user_id)
        with get_conn() as c:
            c.execute(f"UPDATE users SET {', '.join(parts)} WHERE id = ?", args)
    return get_user_by_id(user_id)


def update_account_profile(user_id: int, *, username: str,
                           email: str) -> Optional[sqlite3.Row]:
    return update_user(user_id, username=username, email=email)


def verify_user_password(user_id: int, password: str) -> bool:
    user = get_user_by_id(user_id)
    if not user or not _has_password(user):
        return False
    return bcrypt.checkpw(password.encode("utf-8"),
                          user["password_hash"].encode("utf-8"))


def link_google_account(user_id: int, *, google_sub: str,
                        email: Optional[str] = None,
                        email_verified: bool) -> Optional[sqlite3.Row]:
    current = get_user_by_id(user_id)
    if not current:
        return None
    provider = _merge_auth_provider(current["auth_provider"], "google")
    # Google owns the email once linked; adopt the verified Google address.
    new_email = email or current["email"]
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET google_sub = ?, auth_provider = ?, email = ?, email_verified = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            google_sub, provider, new_email,
            1 if email_verified else current["email_verified"],
            _now(), user_id,
        ))
    return get_user_by_id(user_id)


def unlink_google_account(user_id: int) -> Optional[sqlite3.Row]:
    current = get_user_by_id(user_id)
    if not current:
        return None
    if not _has_password(current):
        raise ValueError("set a password before disconnecting Google")
    provider = "local"
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET google_sub = NULL, auth_provider = ?, updated_at = ?
            WHERE id = ?
        """, (provider, _now(), user_id))
    return get_user_by_id(user_id)


def account_security_summary(user_id: int) -> Optional[dict]:
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        "uid": user["id"],
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
        "auth_provider": user["auth_provider"],
        "email_verified": int(user["email_verified"]),
        "google_linked": bool(user["google_sub"]),
        "two_factor_enabled": bool(user["totp_enabled"]),
        "has_password": _has_password(user),
        # Email is owned by Google while linked and cannot be edited.
        "email_locked": bool(user["google_sub"]),
    }


def set_totp_secret(user_id: int, secret: str) -> None:
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET totp_secret = ?, totp_enabled = 0, totp_confirmed_at = NULL,
                updated_at = ?
            WHERE id = ?
        """, (secret, _now(), user_id))


def enable_totp(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET totp_enabled = 1, totp_confirmed_at = ?, updated_at = ?
            WHERE id = ? AND totp_secret IS NOT NULL
        """, (_now(), _now(), user_id))
    return get_user_by_id(user_id)


def disable_totp(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        c.execute("""
            UPDATE users
            SET totp_secret = NULL, totp_enabled = 0, totp_confirmed_at = NULL,
                updated_at = ?
            WHERE id = ?
        """, (_now(), user_id))
        c.execute("DELETE FROM user_recovery_codes WHERE user_id = ?", (user_id,))
    return get_user_by_id(user_id)


def replace_recovery_codes(user_id: int, codes: Iterable[str]) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM user_recovery_codes WHERE user_id = ?", (user_id,))
        c.executemany("""
            INSERT INTO user_recovery_codes (user_id, code_hash, created_at)
            VALUES (?, ?, ?)
        """, [
            (user_id, _hash_pw(code), _now())
            for code in codes
        ])


def consume_recovery_code(user_id: int, code: str) -> bool:
    with get_conn() as c:
        rows = list(c.execute("""
            SELECT id, code_hash
            FROM user_recovery_codes
            WHERE user_id = ? AND used_at IS NULL
        """, (user_id,)))
        for row in rows:
            if bcrypt.checkpw(code.encode("utf-8"),
                              row["code_hash"].encode("utf-8")):
                c.execute(
                    "UPDATE user_recovery_codes SET used_at = ? WHERE id = ?",
                    (_now(), row["id"]),
                )
                return True
    return False


def delete_user(user_id: int) -> bool:
    user = get_user_by_id(user_id)
    if not user:
        return False
    if user["role"] == "admin":
        raise ValueError("the admin account cannot be deleted")
    with get_conn() as c:
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


def user_has_role(user_id: int, *roles: str) -> bool:
    for role in roles:
        _validate_role(role)
    with get_conn() as c:
        row = c.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    return bool(row and row["role"] in roles)


# ---------- password reset ----------

def create_reset_token(user_id: int, ttl_min: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=ttl_min)).isoformat()
    with get_conn() as c:
        c.execute(
            "INSERT INTO password_resets (token,user_id,expires_at,used,created_at) "
            "VALUES (?,?,?,0,?)", (token, user_id, expires, _now()))
    return token


def consume_reset_token(token: str) -> Optional[int]:
    """Return user_id if token valid+unused+unexpired, marking it used."""
    with get_conn() as c:
        row = c.execute(
            "SELECT user_id, expires_at, used FROM password_resets WHERE token = ?",
            (token,)).fetchone()
        if not row or row["used"]:
            return None
        if row["expires_at"] < _now():
            return None
        c.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
        return int(row["user_id"])


# ---------- email verification ----------

def create_email_verification_token(user_id: int, ttl_min: int = 60 * 24) -> str:
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=ttl_min)).isoformat()
    # Keep previously issued (unused, unexpired) tokens valid: a user sent several
    # verification emails must be able to click any of them, not only the latest.
    # Tokens stay single-use (consume marks the clicked one) and self-expire via TTL.
    with get_conn() as c:
        c.execute("""
            INSERT INTO email_verifications
            (token,user_id,email,expires_at,used,created_at)
            VALUES (?,?,?,?,0,?)
        """, (token, user_id, user["email"], expires, _now()))
    return token


def consume_email_verification_token(token: str) -> Optional[int]:
    """Mark the token used and verify the user's current matching email."""
    with get_conn() as c:
        row = c.execute("""
            SELECT user_id, email, expires_at, used
            FROM email_verifications
            WHERE token = ?
        """, (token,)).fetchone()
        if not row or row["used"]:
            return None
        if row["expires_at"] < _now():
            return None
        user = c.execute(
            "SELECT email FROM users WHERE id = ?",
            (row["user_id"],),
        ).fetchone()
        if not user or str(user["email"]).lower() != str(row["email"]).lower():
            return None
        c.execute("UPDATE email_verifications SET used = 1 WHERE token = ?", (token,))
        c.execute("""
            UPDATE users
            SET email_verified = 1, updated_at = ?
            WHERE id = ?
        """, (_now(), row["user_id"]))
        return int(row["user_id"])


# ---------- courses ----------

def list_courses(*, user_id: Optional[int] = None,
                 role: Optional[str] = None) -> List[sqlite3.Row]:
    sql = """
        SELECT c.*, u.username AS faculty_username,
               (SELECT COUNT(*) FROM course_students cs
                WHERE cs.course_id = c.id) AS student_count,
               (SELECT COUNT(*) FROM lectures l
                WHERE l.course_id = c.id) AS lecture_count
        FROM courses c
        JOIN users u ON u.id = c.faculty_id
        WHERE 1=1
    """
    args: List = []
    if role:
        _validate_role(role)
        if role == "prof":
            sql += " AND c.faculty_id = ?"
            args.append(user_id)
        elif role == "student":
            sql += """
                AND (
                    c.visibility = 'public'
                    OR EXISTS (
                        SELECT 1 FROM course_students cs
                        WHERE cs.course_id = c.id
                          AND cs.user_id = ?
                    )
                )
            """
            args.append(user_id)
    sql += " ORDER BY c.name COLLATE NOCASE"
    with get_conn() as c:
        return list(c.execute(sql, args))


def get_course(course_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("""
            SELECT c.*, u.username AS faculty_username
            FROM courses c
            JOIN users u ON u.id = c.faculty_id
            WHERE c.id = ?
        """, (course_id,)).fetchone()


def can_manage_course(row: sqlite3.Row, *, user_id: int, role: str) -> bool:
    _validate_role(role)
    return role == "admin" or (role == "prof" and row["faculty_id"] == user_id)


def create_course(*, name: str, faculty_id: int,
                  description: Optional[str] = None,
                  visibility: str = "public") -> int:
    if not user_has_role(faculty_id, "prof", "admin"):
        raise ValueError("course owner must be faculty")
    _validate_visibility(visibility)
    now = _now()
    with get_conn() as c:
        cur = c.execute("""
            INSERT INTO courses (name, faculty_id, description, visibility, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, faculty_id, description, visibility, now, now))
        return int(cur.lastrowid)


def update_course(course_id: int, *, name: Optional[str] = None,
                  faculty_id: Optional[int] = None,
                  description: Optional[str] = None,
                  visibility: Optional[str] = None) -> Optional[sqlite3.Row]:
    if faculty_id is not None and not user_has_role(faculty_id, "prof", "admin"):
        raise ValueError("course owner must be faculty")
    if visibility is not None:
        _validate_visibility(visibility)
    parts: List[str] = []
    args: List = []
    if name is not None:
        parts.append("name = ?")
        args.append(name)
    if faculty_id is not None:
        parts.append("faculty_id = ?")
        args.append(faculty_id)
    if description is not None:
        parts.append("description = ?")
        args.append(description)
    if visibility is not None:
        parts.append("visibility = ?")
        args.append(visibility)
    if parts:
        parts.append("updated_at = ?")
        args.append(_now())
        args.append(course_id)
        with get_conn() as c:
            c.execute(f"UPDATE courses SET {', '.join(parts)} WHERE id = ?", args)
            # Lectures follow their course's owner: changing the course faculty
            # re-owns every lecture currently attached to it.
            if faculty_id is not None:
                c.execute(
                    "UPDATE lectures SET owner_user_id = ? WHERE course_id = ?",
                    (faculty_id, course_id))
    return get_course(course_id)


def delete_course(course_id: int) -> bool:
    with get_conn() as c:
        cur = c.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        return cur.rowcount > 0


def list_course_student_ids(course_id: int) -> List[int]:
    with get_conn() as c:
        return [
            int(r["user_id"])
            for r in c.execute(
                "SELECT user_id FROM course_students WHERE course_id = ? ORDER BY user_id",
                (course_id,))
        ]


def list_course_lecture_ids(course_id: int) -> List[str]:
    with get_conn() as c:
        return [
            str(r["id"])
            for r in c.execute(
                "SELECT id FROM lectures WHERE course_id = ? ORDER BY captured_at DESC",
                (course_id,))
        ]


def _ensure_students(conn: sqlite3.Connection, student_ids: List[int]) -> None:
    if not student_ids:
        return
    placeholders = ",".join("?" for _ in student_ids)
    rows = list(conn.execute(
        f"SELECT id FROM users WHERE role = 'student' AND id IN ({placeholders})",
        student_ids))
    found = {int(r["id"]) for r in rows}
    missing = [sid for sid in student_ids if sid not in found]
    if missing:
        raise ValueError("student not found")


def set_course_students(course_id: int, student_ids: Iterable[int]) -> None:
    ids = list(dict.fromkeys(int(s) for s in student_ids))
    with get_conn() as c:
        if not c.execute("SELECT 1 FROM courses WHERE id = ?",
                         (course_id,)).fetchone():
            raise ValueError("course not found")
        _ensure_students(c, ids)
        c.execute("DELETE FROM course_students WHERE course_id = ?", (course_id,))
        c.executemany("""
            INSERT INTO course_students (course_id, user_id, created_at)
            VALUES (?, ?, ?)
        """, [(course_id, sid, _now()) for sid in ids])


def replace_course_lectures(course_id: int, lecture_ids: Iterable[str],
                            owner_user_id: Optional[int] = None) -> None:
    ids = list(dict.fromkeys(str(lid) for lid in lecture_ids))
    with get_conn() as c:
        course = c.execute("SELECT name, faculty_id FROM courses WHERE id = ?",
                           (course_id,)).fetchone()
        if not course:
            raise ValueError("course not found")
        if ids:
            placeholders = ",".join("?" for _ in ids)
            args: List = ids[:]
            owner_clause = ""
            if owner_user_id is not None:
                owner_clause = " AND owner_user_id = ?"
                args.append(owner_user_id)
            rows = list(c.execute(
                f"SELECT id FROM lectures WHERE id IN ({placeholders}){owner_clause}",
                args))
            found = {str(r["id"]) for r in rows}
            missing = [lid for lid in ids if lid not in found]
            if missing:
                raise ValueError("lecture not found")
        if owner_user_id is None:
            c.execute("UPDATE lectures SET course_id = NULL WHERE course_id = ?",
                      (course_id,))
        else:
            c.execute("""
                UPDATE lectures SET course_id = NULL
                WHERE course_id = ?
                  AND owner_user_id = ?
            """, (course_id, owner_user_id))
        # A lecture belongs to exactly one course and is owned by that course's
        # faculty: attaching it here transfers ownership to the course owner.
        c.executemany("""
            UPDATE lectures
            SET course_id = ?, course_name = ?, owner_user_id = ?
            WHERE id = ?
        """, [(course_id, course["name"], course["faculty_id"], lid)
              for lid in ids])


def list_lecture_student_ids(lecture_id: str) -> List[int]:
    with get_conn() as c:
        return [
            int(r["user_id"])
            for r in c.execute(
                "SELECT user_id FROM lecture_students WHERE lecture_id = ? ORDER BY user_id",
                (lecture_id,))
        ]


def set_lecture_students(lecture_id: str, student_ids: Iterable[int]) -> None:
    ids = list(dict.fromkeys(int(s) for s in student_ids))
    with get_conn() as c:
        if not c.execute("SELECT 1 FROM lectures WHERE id = ?",
                         (lecture_id,)).fetchone():
            raise ValueError("lecture not found")
        _ensure_students(c, ids)
        c.execute("DELETE FROM lecture_students WHERE lecture_id = ?", (lecture_id,))
        c.executemany("""
            INSERT INTO lecture_students (lecture_id, user_id, created_at)
            VALUES (?, ?, ?)
        """, [(lecture_id, sid, _now()) for sid in ids])


# ---------- annotations ----------

def add_annotation(lecture_id: str, user_id: int, note: str) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO annotations (lecture_id,user_id,note_text,created_at) VALUES (?,?,?,?)",
            (lecture_id, user_id, note, _now()))
        return int(cur.lastrowid)


def get_annotations(lecture_id: str) -> List[sqlite3.Row]:
    with get_conn() as c:
        return list(c.execute(
            "SELECT a.*, u.username FROM annotations a "
            "LEFT JOIN users u ON u.id = a.user_id "
            "WHERE lecture_id = ? ORDER BY created_at ASC",
            (lecture_id,)))


# ---------- audit ----------

def audit(user_id: Optional[int], action: str, target_id: Optional[str],
          ip: Optional[str]) -> None:
    with get_conn() as c:
        c.execute(
            "INSERT INTO audit_log (user_id,action,target_id,ip_address,timestamp) VALUES (?,?,?,?,?)",
            (user_id, action, target_id, ip, _now()))


def list_audit(limit: int = 500) -> List[sqlite3.Row]:
    with get_conn() as c:
        return list(c.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)))
