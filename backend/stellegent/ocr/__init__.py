"""OCR engine selection: Gemini primary, PP-OCR (RapidOCR) fallback.

``OCR_BACKEND`` controls the choice:

* ``auto``   — Gemini if an API key is set, else PP-OCR. If Gemini errors at
               runtime, fall back to PP-OCR for that call.
* ``gemini`` — force Gemini (raises if no key).
* ``paddle`` — force PP-OCR.

The chosen backend is cached as a singleton; PP-OCR is lazily built only when
first needed (model load is slow).
"""
from __future__ import annotations
import logging
from typing import Optional

import numpy as np

from .base import OCRBackend, OCRLine, OCRResult, lines_to_text
from ..config import settings

log = logging.getLogger(__name__)

_PRIMARY: Optional[OCRBackend] = None
_FALLBACK: Optional[OCRBackend] = None


def _make_paddle() -> OCRBackend:
    from .paddle import PaddleBackend
    return PaddleBackend()


def _make_gemini() -> OCRBackend:
    from .gemini import GeminiCascadeBackend
    return GeminiCascadeBackend(settings.gemini_model_list)


def get_fallback() -> OCRBackend:
    global _FALLBACK
    if _FALLBACK is None:
        _FALLBACK = _make_paddle()
    return _FALLBACK


def get_engine() -> OCRBackend:
    """Return the primary backend per OCR_BACKEND config (cached)."""
    global _PRIMARY
    if _PRIMARY is not None:
        return _PRIMARY
    mode = settings.ocr_backend.lower()
    if mode == "paddle":
        _PRIMARY = get_fallback()
    elif mode == "gemini":
        _PRIMARY = _make_gemini()
    else:  # auto
        _PRIMARY = _make_gemini() if settings.gemini_api_key else get_fallback()
    return _PRIMARY


def run_ocr(img: np.ndarray, engine: Optional[OCRBackend] = None) -> OCRResult:
    """Run OCR. In ``auto`` mode, fall back to PP-OCR if Gemini fails."""
    eng = engine or get_engine()
    try:
        return eng.recognize(img)
    except Exception as e:  # noqa: BLE001
        if settings.ocr_backend.lower() == "auto" and (
            _FALLBACK is None or eng is not _FALLBACK
        ):
            log.warning("primary OCR (%s) failed: %r; falling back to PP-OCR", eng.name, e)
            return get_fallback().recognize(img)
        raise


__all__ = [
    "OCRBackend", "OCRLine", "OCRResult", "lines_to_text",
    "get_engine", "get_fallback", "run_ocr",
]
