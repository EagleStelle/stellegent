"""OCR engine. PaddleOCR v5 (PP-OCRv5, mobile build)."""
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
    """PaddleOCR PP-OCRv5 mobile. Lazy-init; supports both 3.x and 2.x APIs."""
    name = "paddleocr-pp-ocrv5-mobile"

    def __init__(self, lang: str = "en"):
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "PaddleOCR not installed. Install paddlepaddle and paddleocr:\n"
                "  pip install paddlepaddle paddleocr\n"
                "On RPi 5 / ARM64, see https://www.paddlepaddle.org.cn/install/ "
                "for the correct wheel."
            ) from e

        self._is_v3 = False
        self._lang = lang
        try:
            # PaddleOCR 3.x — explicit PP-OCRv5 mobile model names.
            # `lang` and `ocr_version` are ignored when model names are set,
            # so omit them to silence the UserWarning.
            self.ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
                enable_mkldnn=False,
            )
            self._is_v3 = True
        except TypeError:
            raise RuntimeError(
                "Installed PaddleOCR is too old for PP-OCRv5 mobile. "
                "Upgrade: pip install -U 'paddleocr>=3.0' 'paddlepaddle>=3.0'"
            )

    def recognize(self, img: np.ndarray) -> List[OCRLine]:
        if self._is_v3:
            return self._recognize_v3(img)
        return []

    def _recognize_v3(self, img: np.ndarray) -> List[OCRLine]:
        """PaddleOCR 3.x predict() returns list of dicts with rec_texts/scores/polys."""
        results = self.ocr.predict(img)
        out: List[OCRLine] = []
        if not results:
            return out
        for page in results:
            data = page if isinstance(page, dict) else getattr(page, "json", page)
            if hasattr(page, "json") and isinstance(page.json, dict):
                data = page.json.get("res", page.json)
            texts = data.get("rec_texts") or []
            scores = data.get("rec_scores") or []
            polys = data.get("rec_polys") or data.get("dt_polys") or []
            for text, score, poly in zip(texts, scores, polys):
                box = [[float(p[0]), float(p[1])] for p in poly]
                out.append(OCRLine(text=str(text), confidence=float(score), bbox=box))
        return out


_ENGINE: Optional[OCREngine] = None


def make_engine(lang: str = "en") -> OCREngine:
    """PP-OCRv5 mobile, English by default. Tagalog uses Latin script — same model handles it."""
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
