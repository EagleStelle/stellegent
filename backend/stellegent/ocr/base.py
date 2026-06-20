"""OCR backend contract shared by all engines.

Two engine *capabilities* exist:

* layout engines (PP-OCR) return per-line ``OCRLine`` with confidence + bbox,
  so the pipeline can confidence-gate LLM correction.
* text engines (Gemini) return clean ``full_text`` only — no bbox/confidence —
  and self-correct, so the pipeline skips confidence gating for them.

``OCRResult.has_layout`` tells the pipeline which path to take.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Protocol, Sequence, runtime_checkable

import numpy as np


@dataclass
class OCRLine:
    text: str
    confidence: float
    bbox: List[List[float]]  # 4 points clockwise [[x,y]*4]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OCRResult:
    full_text: str
    lines: List[OCRLine] = field(default_factory=list)
    has_layout: bool = True
    engine: str = "unknown"


@runtime_checkable
class OCRBackend(Protocol):
    name: str
    has_layout: bool

    def recognize(self, img: np.ndarray) -> OCRResult: ...


def lines_to_text(lines: Sequence[OCRLine]) -> str:
    """Sort lines top-to-bottom, left-to-right, return plain text."""
    def key(l: OCRLine):
        ys = [p[1] for p in l.bbox]
        xs = [p[0] for p in l.bbox]
        return (round(sum(ys) / len(ys) / 20.0), sum(xs) / len(xs))
    return "\n".join(l.text for l in sorted(lines, key=key))
