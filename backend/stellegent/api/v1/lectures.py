"""Lecture browse / detail / files / annotations / delete."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from ...config import ROOT
from ...db import (list_lectures, get_lecture, delete_lecture,
                   add_annotation, get_annotations)
from ...deps import current_user, require_roles, log_action
from ...schemas import (LectureSummary, LectureDetail, AnnotationOut,
                        AnnotateRequest, MessageResponse)

router = APIRouter(prefix="/lectures", tags=["lectures"])

_FILE_KEYS = {"pdf": "pdf_path", "docx": "docx_path", "txt": "txt_path",
              "image": "image_path", "manifest": "manifest_path"}


@router.get("", response_model=List[LectureSummary])
def list_all(date: Optional[str] = None, course: Optional[str] = None,
             q: Optional[str] = None, _u: dict = Depends(current_user)):
    return [dict(r) for r in list_lectures(date=date, course=course, q=q)]


@router.get("/{lecture_id}", response_model=LectureDetail)
def detail(lecture_id: str, _u: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    out = dict(row)
    try:
        out["manifest"] = json.loads(Path(row["manifest_path"]).read_text("utf-8"))
    except Exception:
        out["manifest"] = None
    out["annotations"] = [dict(a) for a in get_annotations(lecture_id)]
    return out


@router.get("/{lecture_id}/file")
def download(lecture_id: str, request: Request, type: str = "pdf",
             user: dict = Depends(current_user)):
    row = get_lecture(lecture_id)
    if not row:
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
    disposition = "inline" if type == "image" else "attachment"
    return FileResponse(str(p), filename=p.name,
                        content_disposition_type=disposition)


@router.post("/{lecture_id}/annotate", response_model=AnnotationOut, status_code=201)
def annotate(lecture_id: str, body: AnnotateRequest, request: Request,
             user: dict = Depends(current_user)):
    if not get_lecture(lecture_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    nid = add_annotation(lecture_id, user["uid"], body.note.strip())
    log_action(request, user, "annotate", lecture_id)
    notes = [dict(a) for a in get_annotations(lecture_id)]
    return next(a for a in notes if a["id"] == nid)


@router.delete("/{lecture_id}", response_model=MessageResponse)
def remove(lecture_id: str, request: Request,
           user: dict = Depends(require_roles("prof", "admin"))):
    if not get_lecture(lecture_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    delete_lecture(lecture_id)
    log_action(request, user, "delete", lecture_id)
    return MessageResponse(ok=True)
