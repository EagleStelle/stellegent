"""Spelling/grammar correction via local LLM (Ollama)."""
from __future__ import annotations
from typing import List, Sequence

from ..config import OCR_CONFIDENCE_THRESHOLD
from ..ocr.engine import OCRLine
from . import ollama_client

_PROMPT = """You are a strict OCR spell-fixer. Fix ONLY clear spelling typos in the text below.

HARD RULES:
- Do NOT rewrite, rephrase, expand, summarize, translate, or explain.
- Do NOT add words, sentences, punctuation, or formatting that is not already present.
- Do NOT remove words or lines.
- Preserve word count and line breaks exactly.
- Leave unchanged: technical terms, equations, formulas, code, symbols, numbers, abbreviations, proper nouns, and any word you are not certain is misspelled.
- If the entire input looks correct, return it verbatim.
- Output ONLY the corrected text. No preamble, no notes, no quotes.

TEXT:
{text}

CORRECTED:"""


def correct_text(text: str) -> str:
    if not text.strip():
        return text
    out = ollama_client.generate(
        _PROMPT.format(text=text),
        options={"temperature": 0.0, "top_p": 0.1, "num_ctx": 4096, "repeat_penalty": 1.0},
    )
    return out or text


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
