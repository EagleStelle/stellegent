"""End-to-end orchestrator: image -> preprocess -> OCR -> NLP -> export -> DB.

Branches on OCR backend capability: layout engines (PP-OCR) feed the
confidence-gated LLM correction; text engines (Gemini) self-correct, so their
text only gets light postprocessing before summarization.
"""
from __future__ import annotations
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Optional

import cv2
import numpy as np

from .config import DATA_DIR, OCR_CONFIDENCE_THRESHOLD
from .preprocess import preprocess
from .ocr import run_ocr
from .nlp import correct_low_confidence, summarize, generate_title
from .nlp.correct import postprocess
from .export import export_all
from .db import init_db, insert_lecture, update_lecture_processing_timing


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


def _stage(key: str, label: str, started_at: float,
           *, triggered: bool = True) -> dict:
    return {
        "key": key,
        "label": label,
        "duration_ms": _elapsed_ms(started_at) if triggered else 0.0,
        "triggered": triggered,
    }


def _timing_payload(stages: list[dict], total_ms: float) -> dict:
    durations = [
        float(stage["duration_ms"])
        for stage in stages
        if stage.get("triggered", True)
    ]
    return {
        "version": 1,
        "stages": stages,
        "total_ms": total_ms,
        "mean_ms": round(mean(durations), 2) if durations else 0.0,
        "median_ms": round(median(durations), 2) if durations else 0.0,
    }


def process_image(image: np.ndarray, course_name: Optional[str] = None,
                  owner_user_id: Optional[int] = None,
                  visibility: str = "public",
                  course_id: Optional[int] = None) -> dict:
    init_db()
    pipeline_started = perf_counter()
    stages: list[dict] = []

    stage_started = perf_counter()
    rectified = preprocess(image)
    stages.append(_stage("preprocessing", "Preprocessing (OpenCV)", stage_started))

    # OCR reads the raw capture; the preprocessed image is for display/export.
    stage_started = perf_counter()
    result_ocr = run_ocr(image)
    stages.append(_stage("ocr", "OCR (PP-OCRv5)", stage_started))
    raw_text = result_ocr.full_text

    if result_ocr.has_layout:
        stage_started = perf_counter()
        corrected = correct_low_confidence(
            result_ocr.lines, threshold=OCR_CONFIDENCE_THRESHOLD)
        stages.append(_stage(
            "correction",
            "Correction (Phi-3-mini, when triggered)",
            stage_started,
        ))
    else:
        # text engine already self-corrected; just normalize
        corrected = postprocess(raw_text)
        stages.append({
            "key": "correction",
            "label": "Correction (Phi-3-mini, when triggered)",
            "duration_ms": 0.0,
            "triggered": False,
        })

    stage_started = perf_counter()
    summary = summarize(corrected)
    title = generate_title(summary, course_name=course_name)
    stages.append(_stage("summarization", "Summarization (Phi-3-mini)", stage_started))

    stage_started = perf_counter()
    result = export_all(rectified, result_ocr.lines, corrected, summary,
                        base_dir=DATA_DIR, course_name=course_name,
                        raw_text=raw_text, raw_image=image)

    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    insert_lecture(
        lecture_id=result.lecture_id,
        date=result.captured_at[:10],
        course_name=course_name,
        title=title,
        captured_at=result.captured_at,
        image_path=result.image_path,
        raw_image_path=result.raw_image_path,
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
    stages.append(_stage("export_db", "Export + database write", stage_started))
    processing_timing = _timing_payload(stages, _elapsed_ms(pipeline_started))
    update_lecture_processing_timing(result.lecture_id, processing_timing)
    return {
        "lecture_id": result.lecture_id,
        "dir": result.dir,
        "engine": result_ocr.engine,
        "raw_text": raw_text,
        "corrected_text": corrected,
        "summary": summary,
        "title": title,
        "tags": manifest.get("tags", []),
        "processing_timing": processing_timing,
    }


def process_path(path: str, course_name: Optional[str] = None) -> dict:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    return process_image(img, course_name=course_name)
