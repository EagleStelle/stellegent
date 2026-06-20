"""Gemini vision OCR (text engine, primary).

Sends the rectified board image to Gemini via the google-genai SDK and returns
clean transcribed text. Gemini self-corrects spelling/spacing, so the pipeline
skips the confidence-gated LLM correction step for this backend
(``has_layout=False``). SDK is imported lazily so the package still loads when
google-genai is absent or no API key is configured.
"""
from __future__ import annotations

import cv2
import numpy as np

from .base import OCRResult
from ..config import settings

_OCR_PROMPT = (
    "Transcribe ALL text written on this whiteboard exactly as it appears. "
    "Preserve line breaks, bullet/numbered list markers, equations, symbols, "
    "and code verbatim. Fix only obvious handwriting/spelling slips. Do NOT "
    "summarize, translate, add commentary, headings, code fences, or labels. "
    "Output ONLY the transcribed text."
)


class GeminiBackend:
    name = "gemini"
    has_layout = False

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        try:
            from google import genai  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "google-genai not installed. Install it:\n"
                "  pip install google-genai"
            ) from e
        self._client = genai.Client(api_key=self.api_key)

    def recognize(self, img: np.ndarray) -> OCRResult:
        from google.genai import types  # type: ignore

        ok, buf = cv2.imencode(".png", img)
        if not ok:
            raise RuntimeError("failed to encode image for Gemini")
        resp = self._client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=buf.tobytes(), mime_type="image/png"),
                _OCR_PROMPT,
            ],
        )
        text = (resp.text or "").strip()
        return OCRResult(full_text=text, lines=[], has_layout=False, engine=self.name)
