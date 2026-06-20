"""Spelling + light grammar correction via local LLM (Ollama).

Both correction and summarization live in this nlp module and share
``ollama_client``. Correction runs on the full OCR text in one shot so the
model sees context, then the result is validated against the original to
reject hallucinations and post-processed to drop unwanted glyphs and
re-join broken list markers.
"""
from __future__ import annotations
import re
import unicodedata
from typing import List, Sequence

from ..config import OCR_CONFIDENCE_THRESHOLD
from ..ocr.base import OCRLine
from . import ollama_client


# ---------- character filtering ----------
# Unicode block ranges for scripts we don't want in whiteboard transcripts.
# Source: Unicode 15 Blocks.txt — table data, not per-character logic.
# Greek/Cyrillic intentionally kept (Greek letters appear in math/physics).
_DROP_SCRIPT_RANGES: List[tuple] = [
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0x3040, 0x309F),   # Hiragana
    (0x30A0, 0x30FF),   # Katakana
    (0x3100, 0x312F),   # Bopomofo
    (0x3130, 0x318F),   # Hangul Compatibility Jamo
    (0x3190, 0x319F),   # Kanbun
    (0x31A0, 0x31BF),   # Bopomofo Extended
    (0x31C0, 0x31EF),   # CJK Strokes
    (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
    (0x3200, 0x32FF),   # Enclosed CJK Letters
    (0x3300, 0x33FF),   # CJK Compatibility
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0xA000, 0xA4CF),   # Yi Syllables / Radicals
    (0xA960, 0xA97F),   # Hangul Jamo Extended-A
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0xFE30, 0xFE4F),   # CJK Compatibility Forms
    (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth Forms
    (0x1F300, 0x1FAFF), # Misc symbols/pictographs/emoji
    (0x1F600, 0x1F64F), # Emoticons
    (0x1F680, 0x1F6FF), # Transport
    (0x1F700, 0x1F77F),
    (0x1F780, 0x1F7FF),
    (0x1F800, 0x1F8FF),
    (0x1F900, 0x1F9FF),
    (0x1FA00, 0x1FA6F),
    (0x1FA70, 0x1FAFF),
    (0x20000, 0x2FFFF), # CJK Extensions B–F + Supplement
]

_KEEP_SYMBOLS = set("+-*/=<>%&|^~_$@#°±×÷∑∫√π∞≈≠≤≥∈∉∪∩")  # math/board symbols


def _in_dropped_range(cp: int) -> bool:
    for lo, hi in _DROP_SCRIPT_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def _keep_char(ch: str) -> bool:
    cp = ord(ch)
    if ch in "\n\t ":
        return True
    if _in_dropped_range(cp):
        return False
    cat = unicodedata.category(ch)
    if cat.startswith("C"):           # control chars
        return False
    if cat in ("So", "Sk"):           # symbol-other (emoji, dingbats), modifier symbols
        return ch in _KEEP_SYMBOLS
    return True


def _filter_chars(text: str) -> str:
    return "".join(c for c in text if _keep_char(c))


# ---------- format repair ----------
# A "list marker" is leading numbering/bulleting at the start of a logical item.
# Pattern derived from the Markdown / general-text marker grammar, not from
# any specific input string.
_MARKER_RE = re.compile(
    r"""^\s*(
        \#?\d+(?:\.\d+)*[.)\]:]      # 1.  1.2.3)  #5.
      | [a-zA-Z][.)\]:]              # a) A.
      | [-*•·▪◦]                     # bullets
    )\s*$""",
    re.VERBOSE,
)

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANKLINES_RE = re.compile(r"\n{3,}")

# Operator -> regex matching a valid right-operand. If the operator appears
# without that operand, it's stripped. Add new entries here, no per-case logic.
_OPERATOR_OPERAND_RULES = {
    "√": r"\s*[\d(]",   # sqrt needs a digit or opening paren after it
}


def _strip_dangling_operators(text: str) -> str:
    for op, operand in _OPERATOR_OPERAND_RULES.items():
        pattern = re.compile(re.escape(op) + r"(?!" + operand + r")")
        text = pattern.sub("", text)
    return text


def _rejoin_orphan_markers(text: str) -> str:
    """If a line contains nothing but a list marker, glue it to the next
    non-empty line so '#5.\\nEditing...' becomes '#5. Editing...'."""
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = _MARKER_RE.match(ln)
        if m:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                out.append(f"{m.group(1)} {lines[j].lstrip()}")
                i = j + 1
                continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def _normalize_whitespace(text: str) -> str:
    text = _rejoin_orphan_markers(text)
    text = "\n".join(_WHITESPACE_RE.sub(" ", ln).rstrip() for ln in text.split("\n"))
    text = _BLANKLINES_RE.sub("\n\n", text)
    return text.strip()


def postprocess(text: str) -> str:
    return _normalize_whitespace(_strip_dangling_operators(_filter_chars(text)))


_SYSTEM = """You correct OCR errors in whiteboard text. Apply only:
1. Obvious spelling typos (missing/swapped/extra letters).
2. Obvious grammar slips (subject-verb agreement, missing articles, wrong tense).

NEVER do any of the following:
- Rewrite, rephrase, paraphrase, translate, summarize, expand, or shorten.
- Add or remove words, sentences, bullets, or line breaks.
- Change technical terms, equations, formulas, code, numbers, units, symbols, abbreviations, or proper nouns.
- Add commentary, headings, quotes, code fences, or labels.

If a word might be a real technical term, leave it. If unsure, leave it.
Output ONLY the corrected text — same line count, same structure.

Example 1
Input: Pythn is a programing langauge.
Output: Python is a programming language.

Example 2
Input: f(x) = x^2 + 2x + 1
Output: f(x) = x^2 + 2x + 1

Example 3
Input: The mitchondria is the powerhose of teh cell
Output: The mitochondria is the powerhouse of the cell

Example 4
Input: Newton 2nd law: F = ma
Output: Newton's 2nd law: F = ma
"""


_LABEL_RE = re.compile(
    r"^\s*(corrected|output|answer|result|input|text|note|explanation)\s*[:\-]",
    re.IGNORECASE,
)
_RULE_LINE_RE = re.compile(
    r"^\s*[-*\d.)]+\s*(do not|never|always|preserve|leave|if the|output|here is|the corrected)",
    re.IGNORECASE,
)
_FENCE_RE = re.compile(r"^\s*```")


def _strip_artifacts(out: str, original: str) -> str:
    if not out:
        return original

    # If model echoed scaffolding, take text after the LAST output label.
    last = None
    for m in re.finditer(r"(?:corrected|output)\s*[:\-]\s*", out, re.IGNORECASE):
        last = m
    if last is not None:
        out = out[last.end():]

    cleaned: List[str] = []
    for ln in out.splitlines():
        if _LABEL_RE.match(ln) or _RULE_LINE_RE.match(ln) or _FENCE_RE.match(ln):
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned).strip().strip('"').strip("'").strip("`").strip()
    return out or original


def _word_count(s: str) -> int:
    return len(re.findall(r"\S+", s))


def _validate(corrected: str, original: str) -> str:
    """Reject corrections that drift too far from the original. Whiteboard text
    is short and structured; large changes are almost always hallucinations."""
    if not corrected.strip():
        return original

    o_words = _word_count(original)
    c_words = _word_count(corrected)
    if o_words >= 3:
        ratio = c_words / max(o_words, 1)
        if ratio < 0.7 or ratio > 1.3:
            return original

    o_lines = original.count("\n")
    c_lines = corrected.count("\n")
    if abs(c_lines - o_lines) > max(1, o_lines // 4):
        return original

    if len(corrected) > max(80, len(original) * 2):
        return original

    return corrected


def correct_text(text: str) -> str:
    """Correct one chunk of OCR text. Returns original if validation fails."""
    if not text.strip():
        return text
    if len(text.strip()) < 3 or not re.search(r"[A-Za-z]{2,}", text):
        return text
    raw = ollama_client.chat(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Input: {text}\nOutput:"},
        ],
        options={
            "temperature": 0.0,
            "top_p": 0.1,
            "num_ctx": 4096,
            "repeat_penalty": 1.0,
            "stop": ["\nInput:", "\nExample", "\nNote:"],
        },
    )
    cleaned = _strip_artifacts(raw, text)
    validated = _validate(cleaned, text)
    return postprocess(validated)


def correct_low_confidence(lines: Sequence[OCRLine],
                           threshold: float = OCR_CONFIDENCE_THRESHOLD) -> str:
    """Run correction on the full OCR text in one shot when any line is below
    threshold. Single-shot preserves context so the model can disambiguate
    typos against surrounding words. Skip LLM entirely when everything is clean.
    """
    raw_text = "\n".join(l.text for l in lines)
    if not raw_text.strip():
        return raw_text
    if all(l.confidence >= threshold for l in lines):
        return postprocess(raw_text)
    return correct_text(raw_text)
