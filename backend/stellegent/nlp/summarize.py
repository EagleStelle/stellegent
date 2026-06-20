"""Summarization via local LLM (Ollama)."""
from __future__ import annotations
from . import ollama_client

_PROMPT = """Summarize the following lecture board content in 4-8 concise bullet points. Preserve key concepts, definitions, formulas, and step structure. Do not invent facts. Output only the bullets.

LECTURE TEXT:
{text}

SUMMARY:"""


def summarize(text: str) -> str:
    if not text.strip():
        return ""
    return ollama_client.generate(_PROMPT.format(text=text))
