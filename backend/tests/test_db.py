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
    uid = db.create_user("prof1", "secret123", "prof", email="prof1@example.com")
    assert uid > 0
    assert db.verify_user("prof1", "secret123")["role"] == "prof"
    assert db.verify_user("prof1", "wrong") is None
    assert db.verify_user_by_email("PROF1@example.com", "secret123")["role"] == "prof"
    assert db.verify_user_by_email("prof1@example.com", "wrong") is None
    dup_id = db.create_user("prof1", "secret123", "prof", email="prof1b@example.com")
    assert dup_id > uid


def test_lecture_visibility_and_course_access(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "access.db")
    from stellegent import db
    db.init_db()
    prof_id = db.create_user("prof1", "secret123", "prof", email="prof1@example.com")
    student_id = db.create_user("student1", "secret123", "student", email="student1@example.com")
    other_student_id = db.create_user("student2", "secret123", "student", email="student2@example.com")
    course_id = db.create_course(name="Math", faculty_id=prof_id)
    db.set_course_students(course_id, [student_id])

    db.insert_lecture(
        lecture_id="public", date="2026-05-03", course_name="Math",
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="hello", corrected_text="Hello", summary="- hello",
        tags=[], owner_user_id=prof_id, visibility="public",
    )
    db.insert_lecture(
        lecture_id="private-course", date="2026-05-03", course_name="Math",
        captured_at="2026-05-03T11:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="course", corrected_text="Course", summary="- course",
        tags=[], owner_user_id=prof_id, visibility="private",
        course_id=course_id,
    )
    db.insert_lecture(
        lecture_id="private-direct", date="2026-05-03", course_name=None,
        captured_at="2026-05-03T12:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="direct", corrected_text="Direct", summary="- direct",
        tags=[], owner_user_id=prof_id, visibility="private",
    )
    db.set_lecture_students("private-direct", [other_student_id])

    student_rows = db.list_lectures(user_id=student_id, role="student")
    assert {r["id"] for r in student_rows} == {"public", "private-course"}

    other_rows = db.list_lectures(user_id=other_student_id, role="student")
    assert {r["id"] for r in other_rows} == {"public", "private-direct"}

    private_row = db.get_lecture("private-course")
    assert db.can_manage_lecture(private_row, user_id=prof_id, role="prof")
    assert not db.can_manage_lecture(private_row, user_id=student_id, role="student")
