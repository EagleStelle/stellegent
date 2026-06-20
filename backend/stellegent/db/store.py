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

from ..config import DB_PATH
from .migrate import run_migrations


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn(db_path: Optional[Path] = None):
    p = Path(db_path or DB_PATH)
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
                   tags: Iterable[str]) -> None:
    with get_conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO lectures
            (id,date,course_name,captured_at,image_path,docx_path,pdf_path,
             txt_path,manifest_path,raw_ocr_text,corrected_text,summary,tags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (lecture_id, date, course_name, captured_at, image_path,
              docx_path, pdf_path, txt_path, manifest_path,
              raw_ocr_text, corrected_text, summary, json.dumps(list(tags))))


def list_lectures(*, date: Optional[str] = None, course: Optional[str] = None,
                  q: Optional[str] = None, limit: int = 200) -> List[sqlite3.Row]:
    sql = "SELECT * FROM lectures WHERE 1=1"
    args: List = []
    if date:
        sql += " AND date = ?"
        args.append(date)
    if course:
        sql += " AND course_name = ?"
        args.append(course)
    if q:
        sql += " AND (raw_ocr_text LIKE ? OR corrected_text LIKE ? OR summary LIKE ?)"
        like = f"%{q}%"
        args += [like, like, like]
    sql += " ORDER BY captured_at DESC LIMIT ?"
    args.append(limit)
    with get_conn() as c:
        return list(c.execute(sql, args))


def get_lecture(lecture_id: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM lectures WHERE id = ?", (lecture_id,)).fetchone()


def delete_lecture(lecture_id: str) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))


# ---------- users ----------

def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(username: str, password: str, role: str,
                email: Optional[str] = None) -> int:
    if role not in ("prof", "student", "admin"):
        raise ValueError("invalid role")
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (username,password_hash,role,email,auth_provider,"
            "email_verified,created_at) VALUES (?,?,?,?,'local',0,?)",
            (username, _hash_pw(password), role, email, _now()))
        return int(cur.lastrowid)


def get_user(username: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def verify_user(username: str, password: str) -> Optional[sqlite3.Row]:
    u = get_user(username)
    if not u or not u["password_hash"]:
        return None
    if bcrypt.checkpw(password.encode("utf-8"), u["password_hash"].encode("utf-8")):
        return u
    return None


def set_password(user_id: int, password: str) -> None:
    with get_conn() as c:
        c.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                  (_hash_pw(password), user_id))


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
