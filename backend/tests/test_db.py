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


def test_processing_task_queue_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "queue.db")
    from stellegent import db

    db.init_db()
    prof_id = db.create_user(
        "prof1", "secret123", "prof", email="prof1@example.com"
    )
    student_id = db.create_user(
        "student1", "secret123", "student", email="student1@example.com"
    )

    first = db.create_processing_task(
        task_id="task1",
        kind="upload",
        created_by_user_id=prof_id,
        filename="one.jpg",
        payload={"image_path": "/tmp/one.jpg"},
    )
    second = db.create_processing_task(
        task_id="task2",
        kind="capture",
        created_by_user_id=prof_id,
        filename="two.jpg",
        payload={"image_path": "/tmp/two.jpg"},
    )
    assert first["status"] == "queued"
    assert second["queue_position"] == 2

    queued = db.list_processing_tasks(user_id=prof_id, role="prof")
    assert [row["id"] for row in queued] == ["task1", "task2"]

    claimed = db.claim_next_processing_task()
    assert claimed["id"] == "task1"
    assert db.get_processing_task("task1")["status"] == "running"

    db.insert_lecture(
        lecture_id="lecture1", date="2026-05-03", course_name="Math",
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="hello", corrected_text="Hello", summary="- hello",
        tags=[], owner_user_id=prof_id,
    )
    db.complete_processing_task("task1", lecture_id="lecture1")
    assert db.get_processing_task("task1")["status"] == "succeeded"

    db.fail_processing_task("task2", error="decode failed")
    active = db.list_processing_tasks(user_id=prof_id, role="prof")
    assert [row["id"] for row in active] == ["task2"]
    assert active[0]["status"] == "failed"
    assert db.list_processing_tasks(user_id=student_id, role="student") == []


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
    private_course_id = db.create_course(
        name="Hidden Math", faculty_id=prof_id, visibility="private"
    )
    db.set_course_students(course_id, [student_id])
    db.set_course_students(private_course_id, [student_id])

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
    db.insert_lecture(
        lecture_id="public-private-course", date="2026-05-03",
        course_name="Hidden Math",
        captured_at="2026-05-03T13:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="public", corrected_text="Public", summary="- public",
        tags=[], owner_user_id=prof_id, visibility="public",
        course_id=private_course_id,
    )

    student_rows = db.list_lectures(user_id=student_id, role="student")
    assert {r["id"] for r in student_rows} == {
        "public", "private-course", "public-private-course"
    }

    other_rows = db.list_lectures(user_id=other_student_id, role="student")
    assert {r["id"] for r in other_rows} == {
        "public", "private-direct"
    }

    private_row = db.get_lecture("private-course")
    assert db.can_manage_lecture(private_row, user_id=prof_id, role="prof")
    assert not db.can_manage_lecture(private_row, user_id=student_id, role="student")

    public_private_course_row = db.get_lecture("public-private-course")
    assert public_private_course_row["visibility"] == "private"
    assert db.can_view_lecture(
        public_private_course_row, user_id=student_id, role="student"
    )
    assert not db.can_view_lecture(
        public_private_course_row, user_id=other_student_id, role="student"
    )


def test_private_course_privates_existing_lectures(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "course-private.db")
    from stellegent import db

    db.init_db()
    prof_id = db.create_user("prof1", "secret123", "prof", email="prof1@example.com")
    student_id = db.create_user("student1", "secret123", "student", email="student1@example.com")
    other_student_id = db.create_user("student2", "secret123", "student", email="student2@example.com")
    course_id = db.create_course(name="Math", faculty_id=prof_id)
    db.set_course_students(course_id, [student_id])

    db.insert_lecture(
        lecture_id="to-private", date="2026-05-03", course_name="Math",
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="hello", corrected_text="Hello", summary="- hello",
        tags=[], owner_user_id=prof_id, visibility="public",
        course_id=course_id,
    )

    assert "to-private" in {
        r["id"] for r in db.list_lectures(user_id=other_student_id, role="student")
    }

    db.update_course(course_id, visibility="private")
    row = db.get_lecture("to-private")
    assert row["visibility"] == "private"
    assert db.can_view_lecture(row, user_id=student_id, role="student")
    assert not db.can_view_lecture(row, user_id=other_student_id, role="student")
    assert "to-private" not in {
        r["id"] for r in db.list_lectures(user_id=other_student_id, role="student")
    }


def test_adding_lecture_to_private_course_marks_it_private(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "private-assignment.db")
    from stellegent import db

    db.init_db()
    prof_id = db.create_user("prof1", "secret123", "prof", email="prof1@example.com")
    student_id = db.create_user("student1", "secret123", "student", email="student1@example.com")
    course_id = db.create_course(
        name="Hidden Math", faculty_id=prof_id, visibility="private"
    )
    db.set_course_students(course_id, [student_id])
    db.insert_lecture(
        lecture_id="assigned", date="2026-05-03", course_name=None,
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png", docx_path="/tmp/i.docx", pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt", manifest_path="/tmp/m.json",
        raw_ocr_text="hello", corrected_text="Hello", summary="- hello",
        tags=[], owner_user_id=prof_id, visibility="public",
    )

    db.replace_course_lectures(course_id, ["assigned"], owner_user_id=prof_id)

    row = db.get_lecture("assigned")
    assert row["course_id"] == course_id
    assert row["visibility"] == "private"
    assert db.can_view_lecture(row, user_id=student_id, role="student")


def test_student_courses_are_readable_without_management_roster(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "courses.db")
    from stellegent import db
    from stellegent.api.v1 import courses as courses_api

    db.init_db()
    prof_id = db.create_user("prof1", "secret123", "prof", email="prof1@example.com")
    other_prof_id = db.create_user("prof2", "secret123", "prof", email="prof2@example.com")
    student_id = db.create_user("student1", "secret123", "student", email="student1@example.com")
    other_student_id = db.create_user("student2", "secret123", "student", email="student2@example.com")

    public_id = db.create_course(name="Public Math", faculty_id=prof_id, visibility="public")
    assigned_private_id = db.create_course(
        name="Assigned Lab",
        faculty_id=prof_id,
        visibility="private",
    )
    unassigned_private_id = db.create_course(
        name="Closed Seminar",
        faculty_id=other_prof_id,
        visibility="private",
    )
    db.set_course_students(assigned_private_id, [student_id])
    db.set_course_students(unassigned_private_id, [other_student_id])

    rows = courses_api.all_courses({"uid": student_id, "role": "student"})
    assert {row["id"] for row in rows} == {public_id, assigned_private_id}

    opts = courses_api.options({"uid": student_id, "role": "student"})
    assert opts.students == []
    assert {faculty.id for faculty in opts.faculty} == {prof_id}
