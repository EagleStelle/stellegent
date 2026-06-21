"""Ingest + live preview: upload, single-frame capture, MJPEG stream, guidance.

Camera endpoints lazily touch the shared CameraHub, so the API still imports and
serves lecture/auth routes on machines with no camera (e.g. cloud).
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile, status)
from fastapi.responses import StreamingResponse

from ...db import can_manage_course, get_course
from ...db import list_processing_tasks
from ...deps import current_user, require_roles, log_action
from ...processing_queue import enqueue_capture_frame, enqueue_upload_bytes
from ...schemas import CaptureRequest, GuidanceOut, ProcessingTaskOut

router = APIRouter(tags=["capture"])

ALLOWED_UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


def _resolve_course(course_name: Optional[str], course_id: Optional[int],
                    user: dict) -> tuple[Optional[str], Optional[int]]:
    if course_id is None:
        return course_name, None
    course = get_course(course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    if not can_manage_course(course, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    return course["name"], course_id


def _validate_visibility(value: str) -> str:
    if value not in {"public", "private"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid visibility")
    return value


async def _read_upload_limited(image: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await image.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty upload")
    return raw


@router.get("/tasks", response_model=List[ProcessingTaskOut])
def tasks(include_finished: bool = False,
          user: dict = Depends(current_user)):
    return [
        dict(row)
        for row in list_processing_tasks(
            user_id=user["uid"],
            role=user["role"],
            include_finished=include_finished,
        )
    ]


@router.post("/upload", response_model=ProcessingTaskOut,
             status_code=status.HTTP_202_ACCEPTED)
async def upload(request: Request, image: UploadFile = File(...),
                 course: Optional[str] = Form(None),
                 course_id: Optional[int] = Form(None),
                 visibility: str = Form("public"),
                 user: dict = Depends(require_roles("prof", "admin"))):
    ext = Path(image.filename or "").suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"unsupported ext {ext}")
    raw = await _read_upload_limited(image)
    course_name, resolved_course_id = _resolve_course(course or None, course_id, user)
    task = await asyncio.to_thread(
        enqueue_upload_bytes,
        raw=raw,
        extension=ext,
        filename=image.filename,
        course_name=course_name,
        course_id=resolved_course_id,
        owner_user_id=user["uid"],
        visibility=_validate_visibility(visibility),
    )
    log_action(request, user, "upload:queued", task["id"])
    return dict(task)


@router.post("/capture", response_model=ProcessingTaskOut,
             status_code=status.HTTP_202_ACCEPTED)
def capture(request: Request, body: CaptureRequest | None = None,
            user: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub
    frame = get_hub().snapshot()
    if frame is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "camera read failed")
    course_name, course_id = _resolve_course(
        body.course if body else None,
        body.course_id if body else None,
        user,
    )
    task = enqueue_capture_frame(
        frame=frame,
        filename="capture.jpg",
        course_name=course_name,
        course_id=course_id,
        owner_user_id=user["uid"],
        visibility=_validate_visibility(body.visibility if body else "public"),
    )
    log_action(request, user, "capture:queued", task["id"])
    return dict(task)


@router.get("/stream")
def stream(_u: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub
    return StreamingResponse(get_hub().mjpeg(fps=12, overlay=True),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@router.post("/guidance/analyze")
async def guidance_analyze(image: UploadFile = File(...),
                           _u: dict = Depends(require_roles("prof", "admin"))):
    """Analyze a client-supplied frame and return framing guidance as JSON
    (board corners in the submitted image's pixel space + messages + ready).
    The browser draws the overlay on a canvas over its live video, so the video
    stays smooth while the heavy board detection stays on the backend."""
    raw = await image.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "decode failed")
    from ...capture.guidance import analyze_frame
    g = analyze_frame(img)
    h, w = img.shape[:2]
    corners = g.corners.astype(float).tolist() if g.corners is not None else None
    return {
        "width": w,
        "height": h,
        "corners": corners,
        "messages": list(g.messages),
        "ready": bool(g.ready),
    }


@router.get("/guidance", response_model=GuidanceOut)
def guidance(_u: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub, guidance_to_dict
    _, g_res = get_hub().guidance()
    return guidance_to_dict(g_res)
