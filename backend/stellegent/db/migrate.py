"""Tiny forward-only SQL migration runner for SQLite.

Numbered ``migrations/NNN_*.sql`` files apply in order; applied versions are
recorded in ``schema_version``. Idempotent: re-running applies only pending
files. No down-migrations (keep it simple for a single-file SQLite DB).
"""
from __future__ import annotations
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
_NAME_RE = re.compile(r"^(\d+)_.*\.sql$")


def _discover() -> List[Tuple[int, Path]]:
    out: List[Tuple[int, Path]] = []
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = _NAME_RE.match(p.name)
        if m:
            out.append((int(m.group(1)), p))
    out.sort(key=lambda t: t[0])
    return out


def _applied(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    return {row[0] for row in conn.execute("SELECT version FROM schema_version")}


def run_migrations(conn: sqlite3.Connection) -> List[int]:
    """Apply pending migrations on an open connection. Returns versions applied."""
    done = _applied(conn)
    applied: List[int] = []
    for version, path in _discover():
        if version in done:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        applied.append(version)
    conn.commit()
    return applied
