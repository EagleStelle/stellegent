import os
import tempfile
from pathlib import Path

import stellegent.config as cfg


def _patch_db(tmpdir):
    cfg.DB_PATH = Path(tmpdir) / "t.db"


def test_db_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "t.db")
    from stellegent import db
    db.init_db()
    db.insert_lecture(
        lecture_id="abc", date="2026-05-03", course_name="Math",
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="hello", corrected_text="Hello", summary="- hello",
        tags=["math-equations"],
    )
    rows = db.list_lectures()
    assert len(rows) == 1 and rows[0]["id"] == "abc"
    assert db.get_lecture("abc")["course_name"] == "Math"
    db.delete_lecture("abc")
    assert db.get_lecture("abc") is None


def test_user_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "u.db")
    from stellegent import db
    db.init_db()
    uid = db.create_user("prof1", "secret123", "prof")
    assert uid > 0
    assert db.verify_user("prof1", "secret123")["role"] == "prof"
    assert db.verify_user("prof1", "wrong") is None
