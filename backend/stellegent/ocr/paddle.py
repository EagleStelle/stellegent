"""PP-OCR detection + recognition via RapidOCR / onnxruntime (layout engine).

PaddlePaddle's PyPI aarch64 wheels segfault during inference on the Raspberry
Pi 5 (SIGSEGV inside the conv kernels), so inference runs through onnxruntime.
Same PP-OCR weights exported to ONNX — recognition matches PaddleOCR, runtime
is stable on ARM64. Fallback engine when Gemini is unavailable/offline.
"""
from __future__ import annotations
from typing import List

import numpy as np

from .base import OCRLine, OCRResult, lines_to_text


class PaddleBackend:
    name = "rapidocr-onnxruntime-ppocr"
    has_layout = True

    def __init__(self, lang: str = "en"):
        try:
            from rapidocr_onnxruntime import RapidOCR  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "RapidOCR not installed. Install the onnxruntime OCR backend:\n"
                "  pip install rapidocr-onnxruntime onnxruntime"
            ) from e
        self._lang = lang
        self.ocr = RapidOCR()

    def recognize(self, img: np.ndarray) -> OCRResult:
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)
        result, _ = self.ocr(img)
        lines: List[OCRLine] = []
        for box, text, score in (result or []):
            bbox = [[float(p[0]), float(p[1])] for p in box]
            lines.append(OCRLine(text=str(text), confidence=float(score), bbox=bbox))
        return OCRResult(
            full_text=lines_to_text(lines),
            lines=lines,
            has_layout=True,
            engine=self.name,
        )
