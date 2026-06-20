"""Ingest + live preview: upload, single-frame capture, MJPEG stream, guidance.

Camera endpoints lazily touch the shared CameraHub, so the API still imports and
serves lecture/auth routes on machines with no camera (e.g. cloud).
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile, status)
from fastapi.responses import StreamingResponse

from ...deps import require_roles, log_action
from ...pipeline import process_image
from ...schemas import PipelineResult, GuidanceOut, CaptureRequest

router = APIRouter(tags=["capture"])

ALLOWED_UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("/upload", response_model=PipelineResult)
async def upload(request: Request, image: UploadFile = File(...),
                 course: Optional[str] = Form(None),
                 user: dict = Depends(require_roles("prof", "admin"))):
    ext = Path(image.filename or "").suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"unsupported ext {ext}")
    raw = await image.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "decode failed")
    res = process_image(img, course_name=course or None)
    log_action(request, user, "upload", res["lecture_id"])
    return res


@router.post("/capture", response_model=PipelineResult)
def capture(request: Request, body: CaptureRequest | None = None,
            user: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub
    frame = get_hub().snapshot()
    if frame is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "camera read failed")
    res = process_image(frame, course_name=(body.course if body else None))
    log_action(request, user, "capture", res["lecture_id"])
    return res


@router.get("/stream")
def stream(_u: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub
    return StreamingResponse(get_hub().mjpeg(fps=12, overlay=True),
                             media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/guidance", response_model=GuidanceOut)
def guidance(_u: dict = Depends(require_roles("prof", "admin"))):
    from ...capture.hub import get_hub, guidance_to_dict
    _, g_res = get_hub().guidance()
    return guidance_to_dict(g_res)
