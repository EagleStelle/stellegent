from fastapi.testclient import TestClient

import stellegent.config as cfg
from stellegent.main import create_app


def _insert_lecture(db, *, lecture_id: str, owner_user_id: int) -> None:
    db.insert_lecture(
        lecture_id=lecture_id,
        date="2026-05-03",
        course_name="Math",
        captured_at="2026-05-03T10:00:00+00:00",
        image_path="/tmp/i.png",
        docx_path="/tmp/i.docx",
        pdf_path="/tmp/i.pdf",
        txt_path="/tmp/i.txt",
        raw_ocr_text="helo world",
        corrected_text="hello world",
        summary="hello world summary",
        tags=[],
        owner_user_id=owner_user_id,
        visibility="public",
    )


def test_prof_can_save_reference_text_and_receive_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "evaluation-api.db")
    from stellegent import db

    db.init_db()
    prof_id = db.create_user(
        "prof1", "secret123", "prof", email="prof1@example.com"
    )
    _insert_lecture(db, lecture_id="lecture1", owner_user_id=prof_id)

    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/login",
            json={"email": "prof1@example.com", "password": "secret123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        response = client.patch(
            "/api/v1/lectures/lecture1",
            headers=headers,
            json={
                "reference_transcript": "hello world",
                "reference_summary": "hello world summary",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reference_transcript"] == "hello world"
    assert data["reference_summary"] == "hello world summary"
    assert data["evaluation"]["raw_ocr"]["wer"]["error_rate"] == 0.5
    assert data["evaluation"]["corrected"]["wer"]["error_rate"] == 0
    assert data["evaluation"]["summary"]["rouge1"]["fmeasure"] == 1


def test_student_can_see_scores_but_not_reference_text(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "evaluation-privacy.db")
    from stellegent import db

    db.init_db()
    prof_id = db.create_user(
        "prof1", "secret123", "prof", email="prof1@example.com"
    )
    db.create_user(
        "student1", "secret123", "student", email="student1@example.com"
    )
    _insert_lecture(db, lecture_id="lecture1", owner_user_id=prof_id)
    db.update_lecture(
        "lecture1",
        reference_transcript="hello world",
        reference_summary="hello world summary",
    )

    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/login",
            json={"email": "student1@example.com", "password": "secret123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}

        detail = client.get("/api/v1/lectures/lecture1", headers=headers)
        forbidden = client.patch(
            "/api/v1/lectures/lecture1",
            headers=headers,
            json={"reference_transcript": "student edit"},
        )

    assert detail.status_code == 200
    data = detail.json()
    assert data["reference_transcript"] is None
    assert data["reference_summary"] is None
    assert data["evaluation"]["corrected"]["wer"]["error_rate"] == 0
    assert forbidden.status_code == 403
