"""Spelling/grammar correction via local LLM (Ollama)."""
from __future__ import annotations
from typing import List, Sequence

from ..config import OCR_CONFIDENCE_THRESHOLD
from ..ocr.engine import OCRLine
from . import ollama_client

_PROMPT = """You are a careful proofreader. Fix only obvious spelling and grammar errors in the OCR text below. Preserve technical terms, equations, formulas, proper nouns, code, and structure (line breaks, bullets). Do not add or remove content. Output ONLY the corrected text, no explanations.

OCR TEXT:
{text}

CORRECTED:"""


def correct_text(text: str) -> str:
    if not text.strip():
        return text
    return ollama_client.generate(_PROMPT.format(text=text))


def correct_low_confidence(lines: Sequence[OCRLine],
                           threshold: float = OCR_CONFIDENCE_THRESHOLD) -> str:
    """Correct only lines with confidence below threshold; pass others through."""
    parts: List[str] = []
    for line in lines:
        if line.confidence >= threshold:
            parts.append(line.text)
        else:
            parts.append(correct_text(line.text))
    return "\n".join(parts)
