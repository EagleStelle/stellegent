"""End-to-end orchestrator: image -> preprocess -> OCR -> NLP -> export -> DB.

Branches on OCR backend capability: layout engines (PP-OCR) feed the
confidence-gated LLM correction; text engines (Gemini) self-correct, so their
text only gets light postprocessing before summarization.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .config import DATA_DIR, OCR_CONFIDENCE_THRESHOLD
from .preprocess import preprocess
from .ocr import run_ocr
from .nlp import correct_low_confidence, summarize
from .nlp.correct import postprocess
from .export import export_all
from .db import init_db, insert_lecture


def process_image(image: np.ndarray, course_name: Optional[str] = None,
                  owner_user_id: Optional[int] = None,
                  visibility: str = "public",
                  course_id: Optional[int] = None) -> dict:
    init_db()
    rectified = preprocess(image)
    result_ocr = run_ocr(rectified)
    raw_text = result_ocr.full_text

    if result_ocr.has_layout:
        corrected = correct_low_confidence(
            result_ocr.lines, threshold=OCR_CONFIDENCE_THRESHOLD)
    else:
        # text engine already self-corrected; just normalize
        corrected = postprocess(raw_text)

    summary = summarize(corrected)

    result = export_all(rectified, result_ocr.lines, corrected, summary,
                        base_dir=DATA_DIR, course_name=course_name,
                        raw_text=raw_text)

    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    insert_lecture(
        lecture_id=result.lecture_id,
        date=result.captured_at[:10],
        course_name=course_name,
        captured_at=result.captured_at,
        image_path=result.image_path,
        docx_path=result.docx_path,
        pdf_path=result.pdf_path,
        txt_path=result.txt_path,
        manifest_path=result.manifest_path,
        raw_ocr_text=raw_text,
        corrected_text=corrected,
        summary=summary,
        tags=manifest.get("tags", []),
        owner_user_id=owner_user_id,
        visibility=visibility,
        course_id=course_id,
    )
    return {
        "lecture_id": result.lecture_id,
        "dir": result.dir,
        "engine": result_ocr.engine,
        "raw_text": raw_text,
        "corrected_text": corrected,
        "summary": summary,
        "tags": manifest.get("tags", []),
    }


def process_path(path: str, course_name: Optional[str] = None) -> dict:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    return process_image(img, course_name=course_name)
