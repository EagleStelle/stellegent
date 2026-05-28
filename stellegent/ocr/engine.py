"""OCR engine. PP-OCR models via RapidOCR (onnxruntime backend).

PaddlePaddle's PyPI aarch64 wheels segfault during inference on the Raspberry
Pi 5 (SIGSEGV inside the conv kernels, even single-threaded with MKL-DNN off),
so inference runs through onnxruntime instead of paddle. The detection and
recognition models are the same PP-OCR weights exported to ONNX, so recognition
accuracy matches PaddleOCR while the runtime is stable on ARM64.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional, Sequence
import numpy as np


@dataclass
class OCRLine:
    text: str
    confidence: float
    bbox: List[List[float]]  # 4 points clockwise [[x,y]*4]

    def to_dict(self) -> dict:
        return asdict(self)


class OCREngine:
    """PP-OCR detection + recognition via RapidOCR / onnxruntime. Lazy-init."""
    name = "rapidocr-onnxruntime-ppocr"

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

    def recognize(self, img: np.ndarray) -> List[OCRLine]:
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)
        result, _ = self.ocr(img)
        out: List[OCRLine] = []
        if not result:
            return out
        for box, text, score in result:
            bbox = [[float(p[0]), float(p[1])] for p in box]
            out.append(OCRLine(text=str(text), confidence=float(score), bbox=bbox))
        return out


_ENGINE: Optional[OCREngine] = None


def make_engine(lang: str = "en") -> OCREngine:
    """PP-OCR English by default. Tagalog uses Latin script — same model handles it."""
    return OCREngine(lang=lang)


def get_engine(lang: str = "en") -> OCREngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = make_engine(lang=lang)
    return _ENGINE


def run_ocr(img: np.ndarray, engine: Optional[OCREngine] = None,
            lang: str = "en") -> List[OCRLine]:
    eng = engine or get_engine(lang=lang)
    return eng.recognize(img)


def lines_to_text(lines: Sequence[OCRLine]) -> str:
    """Sort lines top-to-bottom, left-to-right, return plain text."""
    def key(l: OCRLine):
        ys = [p[1] for p in l.bbox]
        xs = [p[0] for p in l.bbox]
        return (round(sum(ys) / len(ys) / 20.0), sum(xs) / len(xs))
    return "\n".join(l.text for l in sorted(lines, key=key))
