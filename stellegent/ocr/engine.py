"""OCR wrapper: PaddleOCR primary, EasyOCR fallback. Unified output schema."""
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
    name = "base"

    def recognize(self, img: np.ndarray) -> List[OCRLine]:
        raise NotImplementedError


class PaddleEngine(OCREngine):
    name = "paddleocr"

    def __init__(self, lang: str = "en"):
        from paddleocr import PaddleOCR  # type: ignore
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def recognize(self, img: np.ndarray) -> List[OCRLine]:
        raw = self.ocr.ocr(img, cls=True)
        lines: List[OCRLine] = []
        if not raw or not raw[0]:
            return lines
        for entry in raw[0]:
            box, (text, conf) = entry
            lines.append(OCRLine(text=text, confidence=float(conf),
                                 bbox=[[float(x), float(y)] for x, y in box]))
        return lines


class EasyEngine(OCREngine):
    name = "easyocr"

    def __init__(self, langs: Sequence[str] = ("en",)):
        import easyocr  # type: ignore
        self.reader = easyocr.Reader(list(langs), gpu=False)

    def recognize(self, img: np.ndarray) -> List[OCRLine]:
        results = self.reader.readtext(img)
        out: List[OCRLine] = []
        for box, text, conf in results:
            out.append(OCRLine(text=str(text), confidence=float(conf),
                               bbox=[[float(x), float(y)] for x, y in box]))
        return out


def make_engine(prefer: str = "paddle", lang: str = "en") -> OCREngine:
    if prefer == "paddle":
        try:
            return PaddleEngine(lang=lang)
        except Exception as e:
            print(f"[ocr] paddle init failed: {e}; falling back to easyocr")
    return EasyEngine(langs=[lang])


def run_ocr(img: np.ndarray, engine: Optional[OCREngine] = None,
            lang: str = "en") -> List[OCRLine]:
    if engine is None:
        engine = make_engine(lang=lang)
    return engine.recognize(img)


def lines_to_text(lines: Sequence[OCRLine]) -> str:
    """Sort lines top-to-bottom, left-to-right, return plain text."""
    def key(l: OCRLine):
        ys = [p[1] for p in l.bbox]
        xs = [p[0] for p in l.bbox]
        return (round(sum(ys) / len(ys) / 20.0), sum(xs) / len(xs))
    return "\n".join(l.text for l in sorted(lines, key=key))
