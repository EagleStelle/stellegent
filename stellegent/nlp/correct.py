"""Spelling correction via local LLM (Ollama)."""
from __future__ import annotations
import re
from typing import List, Sequence

from ..config import OCR_CONFIDENCE_THRESHOLD
from ..ocr.engine import OCRLine
from . import ollama_client

_SYSTEM = (
    "You are a strict OCR spelling fixer. "
    "Fix only obvious spelling typos in the user's text. "
    "Do not rewrite, rephrase, expand, summarize, translate, explain, or comment. "
    "Do not add or remove words, lines, punctuation, or formatting. "
    "Preserve word count and line breaks exactly. "
    "Leave unchanged: technical terms, equations, formulas, code, symbols, "
    "numbers, abbreviations, proper nouns, and any word you are not certain is misspelled. "
    "If the input looks correct, return it verbatim. "
    "Output ONLY the corrected text. No preamble, no notes, no quotes, no labels."
)

_LABEL_PATTERNS = [
    re.compile(r"^\s*(corrected|output|answer|result)\s*[:\-]\s*", re.IGNORECASE),
    re.compile(r"^\s*```.*$"),
    re.compile(r"^\s*hard rules\s*[:\-]?\s*$", re.IGNORECASE),
    re.compile(r"^\s*text\s*[:\-]\s*$", re.IGNORECASE),
]

_MIN_CORRECT_LEN = 3  # don't send 1-2 char fragments to LLM


def _strip_artifacts(out: str, original: str) -> str:
    """Remove model echo / wrappers / labels. Fall back to original if mangled."""
    if not out:
        return original

    # If model parroted the prompt, prefer text after the LAST "CORRECTED:" label.
    m = list(re.finditer(r"corrected\s*[:\-]\s*", out, re.IGNORECASE))
    if m:
        out = out[m[-1].end():]

    lines = out.splitlines()
    cleaned: List[str] = []
    for ln in lines:
        if any(p.match(ln) for p in _LABEL_PATTERNS):
            continue
        # Drop lines that start with a bullet describing rules.
        if re.match(r"^\s*-\s*(do not|preserve|leave|if the|output)", ln, re.IGNORECASE):
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned).strip().strip('"').strip("'").strip("`").strip()

    if not out:
        return original

    # Sanity: corrected length should be in the same ballpark as input.
    if len(out) > max(80, len(original) * 4):
        return original
    return out


def correct_text(text: str) -> str:
    if not text.strip():
        return text
    if len(text.strip()) < _MIN_CORRECT_LEN or not re.search(r"[A-Za-z]{2,}", text):
        return text
    raw = ollama_client.chat(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
        options={
            "temperature": 0.0,
            "top_p": 0.1,
            "num_ctx": 4096,
            "repeat_penalty": 1.0,
            "stop": ["\nTEXT:", "\nCORRECTED:", "HARD RULES"],
        },
    )
    return _strip_artifacts(raw, text)


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
