"""Spelling/grammar correction. LLM via Ollama, SymSpell rule-based fallback."""
from __future__ import annotations
import re
from typing import List, Optional, Sequence

from ..config import OCR_CONFIDENCE_THRESHOLD
from ..ocr.engine import OCRLine
from . import ollama_client

_PROMPT = """You are a careful proofreader. Fix only obvious spelling and grammar errors in the OCR text below. Preserve technical terms, equations, formulas, proper nouns, code, and structure (line breaks, bullets). Do not add or remove content. Output ONLY the corrected text, no explanations.

OCR TEXT:
{text}

CORRECTED:"""


def _llm_correct(text: str) -> str:
    return ollama_client.generate(_PROMPT.format(text=text))


def _symspell_correct(text: str) -> str:
    try:
        from symspellpy import SymSpell, Verbosity  # type: ignore
        import pkg_resources  # type: ignore
        sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        dict_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_82_765.txt")
        sym.load_dictionary(dict_path, term_index=0, count_index=1)
        out_tokens: List[str] = []
        for tok in re.findall(r"\S+|\s+", text):
            if tok.isspace() or not tok.isalpha():
                out_tokens.append(tok)
                continue
            sug = sym.lookup(tok, Verbosity.CLOSEST,
                             max_edit_distance=2, include_unknown=True)
            out_tokens.append(sug[0].term if sug else tok)
        return "".join(out_tokens)
    except Exception:
        return text


def correct_text(text: str, prefer_llm: bool = True) -> str:
    if not text.strip():
        return text
    if prefer_llm and ollama_client.is_available():
        try:
            return _llm_correct(text)
        except Exception as e:
            print(f"[nlp] LLM correction failed: {e}; using symspell")
    return _symspell_correct(text)


def correct_low_confidence(lines: Sequence[OCRLine],
                           threshold: float = OCR_CONFIDENCE_THRESHOLD,
                           prefer_llm: bool = True) -> str:
    """Correct only lines with confidence below threshold; pass others through."""
    parts: List[str] = []
    for line in lines:
        if line.confidence >= threshold:
            parts.append(line.text)
        else:
            parts.append(correct_text(line.text, prefer_llm=prefer_llm))
    return "\n".join(parts)
