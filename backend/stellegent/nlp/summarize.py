"""Summarization via local LLM (Ollama)."""
from __future__ import annotations
import logging
from typing import Optional

import requests

from . import ollama_client

log = logging.getLogger(__name__)

_PROMPT = """Summarize the following lecture board content in 4-8 concise bullet points. Preserve key concepts, definitions, formulas, and step structure. Do not invent facts. Output only the bullets.

LECTURE TEXT:
{text}

SUMMARY:"""

_TITLE_PROMPT = """Write a 3 to 5 word title for the lecture below, capturing its main topic. Title Case. No quotes, no punctuation, no trailing period. Output only the title.

LECTURE SUMMARY:
{summary}

TITLE:"""


def summarize(text: str) -> str:
    if not text.strip():
        return ""
    try:
        return ollama_client.generate(_PROMPT.format(text=text))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        # Ollama unreachable/slow — degrade gracefully so the rest of the
        # pipeline (OCR, export, DB) still completes.
        log.warning("summarize skipped: Ollama unavailable (%s)", e)
        return ""


def _clean_title(raw: str) -> str:
    # Models sometimes wrap or over-explain; keep the first line, strip quotes,
    # punctuation, and cap at 5 words.
    line = raw.strip().splitlines()[0] if raw.strip() else ""
    line = line.strip().strip("\"'").rstrip(".").strip()
    words = line.split()
    return " ".join(words[:5])


def generate_title(summary: str, course_name: Optional[str] = None) -> str:
    """Build "<Course name>: <3-5 word title>" from the summary.

    Falls back to the course name (or empty) if the LLM is unavailable or the
    summary is empty, so the pipeline never blocks on title generation.
    """
    topic = ""
    if summary.strip():
        try:
            topic = _clean_title(
                ollama_client.generate(_TITLE_PROMPT.format(summary=summary)))
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            log.warning("title skipped: Ollama unavailable (%s)", e)
    course = (course_name or "").strip()
    if course and topic:
        return f"{course}: {topic}"
    return topic or course
