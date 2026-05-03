"""End-to-end orchestrator: image -> preprocess -> OCR -> NLP -> export -> DB."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

from .config import DATA_DIR, OCR_CONFIDENCE_THRESHOLD
from .preprocess import preprocess
from .ocr.engine import get_engine, run_ocr, lines_to_text, OCREngine
from .nlp import correct_low_confidence, summarize
from .export import export_all
from .db import init_db, insert_lecture


def process_image(image: np.ndarray, course_name: Optional[str] = None) -> dict:
    init_db()
    rectified = preprocess(image)
    lines = run_ocr(rectified, engine=get_engine())
    raw_text = lines_to_text(lines)
    corrected = correct_low_confidence(lines, threshold=OCR_CONFIDENCE_THRESHOLD)
    summary = summarize(corrected)

    result = export_all(rectified, lines, corrected, summary,
                        base_dir=DATA_DIR, course_name=course_name)

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
    )
    return {
        "lecture_id": result.lecture_id,
        "dir": result.dir,
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
