"""OCR transcript and summary evaluation metrics."""
from __future__ import annotations

from collections import Counter
import re
from typing import Sequence, TypeVar

T = TypeVar("T")

_WS_RE = re.compile(r"\s+")
_ROUGE_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _normalize_text(text: str | None) -> str:
    return _WS_RE.sub(" ", (text or "").lower()).strip()


def _char_tokens(text: str | None) -> list[str]:
    return list(_normalize_text(text))


def _word_tokens(text: str | None) -> list[str]:
    normalized = _normalize_text(text)
    return normalized.split() if normalized else []


def _rouge_tokens(text: str | None) -> list[str]:
    return _ROUGE_TOKEN_RE.findall(_normalize_text(text))


def _add_counts(counts: tuple[int, int, int, int], *, sub: int = 0,
                ins: int = 0, delete: int = 0) -> tuple[int, int, int, int]:
    errors, substitutions, insertions, deletions = counts
    return (
        errors + sub + ins + delete,
        substitutions + sub,
        insertions + ins,
        deletions + delete,
    )


def _prefer_counts(counts: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    errors, substitutions, insertions, deletions = counts
    # Prefer substitutions over delete+insert paths when costs tie; this keeps
    # operation counts intuitive while leaving the edit distance unchanged.
    return (errors, insertions + deletions, substitutions, insertions)


def _edit_counts(reference: Sequence[T],
                 hypothesis: Sequence[T]) -> tuple[int, int, int, int]:
    previous = [(j, 0, j, 0) for j in range(len(hypothesis) + 1)]
    for i, ref_unit in enumerate(reference, start=1):
        current: list[tuple[int, int, int, int]] = [(i, 0, 0, i)]
        for j, hyp_unit in enumerate(hypothesis, start=1):
            if ref_unit == hyp_unit:
                current.append(previous[j - 1])
                continue
            substitute = _add_counts(previous[j - 1], sub=1)
            insert = _add_counts(current[j - 1], ins=1)
            delete = _add_counts(previous[j], delete=1)
            current.append(min((substitute, insert, delete),
                               key=_prefer_counts))
        previous = current
    return previous[-1]


def _error_metric(reference_units: Sequence[T],
                  hypothesis_units: Sequence[T]) -> dict | None:
    reference_length = len(reference_units)
    if reference_length == 0:
        return None
    errors, substitutions, insertions, deletions = _edit_counts(
        reference_units, hypothesis_units
    )
    error_rate = errors / reference_length
    return {
        "errors": errors,
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
        "reference_length": reference_length,
        "hypothesis_length": len(hypothesis_units),
        "error_rate": error_rate,
        "recognition_rate": 1 - error_rate,
    }


def score_transcript(*, hypothesis: str | None,
                     reference: str | None) -> dict | None:
    """Return CER/CRR and WER/WRR scores, or None without ground truth."""
    if not _normalize_text(reference):
        return None
    cer = _error_metric(_char_tokens(reference), _char_tokens(hypothesis))
    wer = _error_metric(_word_tokens(reference), _word_tokens(hypothesis))
    if cer is None or wer is None:
        return None
    return {"cer": cer, "wer": wer}


def _ngrams(tokens: Sequence[str], size: int) -> Counter[tuple[str, ...]]:
    if size <= 0 or len(tokens) < size:
        return Counter()
    return Counter(tuple(tokens[i:i + size])
                   for i in range(len(tokens) - size + 1))


def _prf(*, overlap: int, hypothesis_count: int,
         reference_count: int) -> dict:
    precision = overlap / hypothesis_count if hypothesis_count else 0.0
    recall = overlap / reference_count if reference_count else 0.0
    fmeasure = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )
    return {"precision": precision, "recall": recall, "fmeasure": fmeasure}


def _rouge_n(hypothesis_tokens: Sequence[str],
             reference_tokens: Sequence[str], size: int) -> dict:
    hypothesis_counts = _ngrams(hypothesis_tokens, size)
    reference_counts = _ngrams(reference_tokens, size)
    overlap = sum((hypothesis_counts & reference_counts).values())
    return _prf(
        overlap=overlap,
        hypothesis_count=sum(hypothesis_counts.values()),
        reference_count=sum(reference_counts.values()),
    )


def _lcs_len(a: Sequence[str], b: Sequence[str]) -> int:
    previous = [0] * (len(b) + 1)
    for left in a:
        current = [0]
        for j, right in enumerate(b, start=1):
            if left == right:
                current.append(previous[j - 1] + 1)
            else:
                current.append(max(previous[j], current[j - 1]))
        previous = current
    return previous[-1]


def score_summary(*, hypothesis: str | None,
                  reference: str | None) -> dict | None:
    """Return ROUGE-1, ROUGE-2 and ROUGE-L scores, or None without reference."""
    reference_tokens = _rouge_tokens(reference)
    if not reference_tokens:
        return None
    hypothesis_tokens = _rouge_tokens(hypothesis)
    lcs = _lcs_len(hypothesis_tokens, reference_tokens)
    return {
        "rouge1": _rouge_n(hypothesis_tokens, reference_tokens, 1),
        "rouge2": _rouge_n(hypothesis_tokens, reference_tokens, 2),
        "rougeL": _prf(
            overlap=lcs,
            hypothesis_count=len(hypothesis_tokens),
            reference_count=len(reference_tokens),
        ),
    }


def evaluate_lecture(*, raw_ocr_text: str | None,
                     corrected_text: str | None,
                     summary: str | None,
                     reference_transcript: str | None,
                     reference_summary: str | None) -> dict:
    return {
        "raw_ocr": score_transcript(
            hypothesis=raw_ocr_text,
            reference=reference_transcript,
        ),
        "corrected": score_transcript(
            hypothesis=corrected_text,
            reference=reference_transcript,
        ),
        "summary": score_summary(
            hypothesis=summary,
            reference=reference_summary,
        ),
    }
