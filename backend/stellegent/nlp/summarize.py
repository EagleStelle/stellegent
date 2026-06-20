"""Summarization via local LLM (Ollama)."""
from __future__ import annotations
import logging

import requests

from . import ollama_client

log = logging.getLogger(__name__)

_PROMPT = """Summarize the following lecture board content in 4-8 concise bullet points. Preserve key concepts, definitions, formulas, and step structure. Do not invent facts. Output only the bullets.

LECTURE TEXT:
{text}

SUMMARY:"""


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
