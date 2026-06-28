"""Lecture browse / detail / files / annotations / delete."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from ...config import ROOT
from ...db import (can_manage_lecture, can_view_lecture, delete_lecture,
                   get_course, get_lecture, list_lecture_student_ids,
                   list_lectures, set_lecture_students, update_lecture,
                   user_has_role, add_annotation, get_annotations)
from ...deps import current_user, log_action
from ...evaluation import evaluate_lecture
from ...export import write_documents
from ...nlp import summarize, generate_title
from ...schemas import (LectureSummary, LectureDetail, AnnotationOut,
                        AnnotateRequest, LectureUpdateRequest,
                        MessageResponse)

router = APIRouter(prefix="/lectures", tags=["lectures"])

_FILE_KEYS = {"pdf": "pdf_path", "docx": "docx_path", "txt": "txt_path",
              "image": "image_path", "image_raw": "raw_image_path"}
_INLINE_TYPES = {"image", "image_raw"}


def _clean_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


@router.get("", response_model=List[LectureSummary])
def list_all(date: Optional[str] = None, course: Optional[str] = None,
             q: Optional[str] = None, user: dict = Depends(current_user)):
    return [
        dict(r)
        for r in list_lectures(date=date, course=course, q=q,
                               user_id=user["uid"], role=user["role"])
    ]


def _detail_payload(row, user: dict) -> dict:
    out = dict(row)
    out["evaluation"] = evaluate_lecture(
        raw_ocr_text=row["raw_ocr_text"],
        corrected_text=row["corrected_text"],
        summary=row["summary"],
        reference_transcript=row["reference_transcript"],
        reference_summary=row["reference_summary"],
    )
    try:
        out["processing_timing"] = (
            json.loads(row["processing_timing"])
            if row["processing_timing"] else None
        )
    except Exception:
        out["processing_timing"] = None
    out["student_ids"] = list_lecture_student_ids(row["id"])
    out["annotations"] = [dict(a) for a in get_annotations(row["id"])]
    if not can_manage_lecture(row, user_id=user["uid"], role=user["role"]):
        out["reference_transcript"] = None
        out["reference_summary"] = None
    return out


@router.get("/{lecture_id}", response_model=LectureDetail)
def detail(lecture_id: str, user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row or not can_view_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return _detail_payload(row, user)


@router.get("/{lecture_id}/file")
def download(lecture_id: str, request: Request, type: str = "pdf",
             user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row or not can_view_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    key = _FILE_KEYS.get(type)
    if not key or not row[key]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such file")
    p = Path(row[key])
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file missing")
    log_action(request, user, f"download:{type}", lecture_id)
    disposition = "inline" if type in _INLINE_TYPES else "attachment"
    return FileResponse(str(p), filename=p.name,
                        content_disposition_type=disposition)


@router.post("/{lecture_id}/annotate", response_model=AnnotationOut, status_code=201)
def annotate(lecture_id: str, body: AnnotateRequest, request: Request,
             user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    nid = add_annotation(lecture_id, user["uid"], body.note.strip())
    log_action(request, user, "annotate", lecture_id)
    notes = [dict(a) for a in get_annotations(lecture_id)]
    return next(a for a in notes if a["id"] == nid)


@router.post("/{lecture_id}/summarize", response_model=LectureDetail)
def regenerate_summary(lecture_id: str, request: Request,
                       user: dict = Depends(current_user)):
    """Regenerate the summary from the transcript via Ollama, then rewrite the
    downloadable documents so PDF/DOCX/TXT stay in sync."""
    row = get_lecture(lecture_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    source = (row["corrected_text"] or row["raw_ocr_text"] or "").strip()
    new_summary = summarize(source)
    updates = {"summary": new_summary}
    # Title only generated when the lecture has none yet; never overwrite a
    # title the owner has set.
    if not (row["title"] or "").strip():
        new_title = generate_title(new_summary, course_name=row["course_name"])
        if new_title:
            updates["title"] = new_title
    update_lecture(lecture_id, **updates)
    if row["docx_path"] and row["pdf_path"] and row["txt_path"]:
        try:
            write_documents(docx_path=row["docx_path"], pdf_path=row["pdf_path"],
                            txt_path=row["txt_path"], summary=new_summary,
                            corrected=row["corrected_text"] or "")
        except Exception:  # noqa: BLE001 — DB summary already saved; files best-effort
            pass
    log_action(request, user, "summarize", lecture_id)
    return _detail_payload(get_lecture(lecture_id), user)


@router.patch("/{lecture_id}", response_model=LectureDetail)
def update(lecture_id: str, body: LectureUpdateRequest, request: Request,
           user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")

    fields = body.model_fields_set
    updates = {}
    if "title" in fields:
        updates["title"] = body.title
    if "course_name" in fields:
        updates["course_name"] = body.course_name
    if "summary" in fields:
        updates["summary"] = body.summary
    if "corrected_text" in fields:
        updates["corrected_text"] = body.corrected_text
    if "reference_transcript" in fields:
        updates["reference_transcript"] = _clean_optional_text(
            body.reference_transcript
        )
    if "reference_summary" in fields:
        updates["reference_summary"] = _clean_optional_text(
            body.reference_summary
        )
    if "visibility" in fields and body.visibility is not None:
        updates["visibility"] = body.visibility
    if "owner_user_id" in fields:
        if user["role"] != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        if body.owner_user_id is not None and not user_has_role(
            body.owner_user_id, "prof", "admin"
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "lecture owner must be faculty")
        updates["owner_user_id"] = body.owner_user_id
    if "course_id" in fields:
        if body.course_id is not None:
            course = get_course(body.course_id)
            if not course:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
            if user["role"] != "admin" and course["faculty_id"] != user["uid"]:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        updates["course_id"] = body.course_id

    try:
        updated = update_lecture(lecture_id, **updates)
        if "student_ids" in fields and body.student_ids is not None:
            set_lecture_students(lecture_id, body.student_ids)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    refreshed = get_lecture(lecture_id)
    # Keep the downloadable docs in sync when the text changed (also re-renders
    # them through the current PDF/TXT writers).
    if ({"summary", "corrected_text"} & fields) and refreshed["docx_path"] \
            and refreshed["pdf_path"] and refreshed["txt_path"]:
        try:
            write_documents(docx_path=refreshed["docx_path"],
                            pdf_path=refreshed["pdf_path"],
                            txt_path=refreshed["txt_path"],
                            summary=refreshed["summary"] or "",
                            corrected=refreshed["corrected_text"] or "")
        except Exception:  # noqa: BLE001 — DB already saved; files best-effort
            pass
    log_action(request, user, "update_lecture", lecture_id)
    return _detail_payload(refreshed, user)


@router.delete("/{lecture_id}", response_model=MessageResponse)
def remove(lecture_id: str, request: Request,
           user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_lecture(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    delete_lecture(lecture_id)
    log_action(request, user, "delete", lecture_id)
    return MessageResponse(ok=True)
