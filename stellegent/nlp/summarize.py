"""Summarization: Ollama LLM, sumy LSA fallback."""
from __future__ import annotations
from . import ollama_client

_PROMPT = """Summarize the following lecture board content in 4-8 concise bullet points. Preserve key concepts, definitions, formulas, and step structure. Do not invent facts. Output only the bullets.

LECTURE TEXT:
{text}

SUMMARY:"""


def _llm_summarize(text: str) -> str:
    return ollama_client.generate(_PROMPT.format(text=text))


def _sumy_summarize(text: str, sentences: int = 6) -> str:
    try:
        from sumy.parsers.plaintext import PlaintextParser  # type: ignore
        from sumy.nlp.tokenizers import Tokenizer  # type: ignore
        from sumy.summarizers.lsa import LsaSummarizer  # type: ignore
        try:
            import nltk  # type: ignore
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            import nltk
            nltk.download("punkt", quiet=True)
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summ = LsaSummarizer()
        return "\n".join(f"- {s}" for s in summ(parser.document, sentences))
    except Exception:
        # last resort: first N sentences
        parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
        return "\n".join(f"- {p}." for p in parts[:sentences])


def summarize(text: str, prefer_llm: bool = True) -> str:
    if not text.strip():
        return ""
    if prefer_llm and ollama_client.is_available():
        try:
            return _llm_summarize(text)
        except Exception as e:
            print(f"[nlp] LLM summarize failed: {e}; using sumy")
    return _sumy_summarize(text)
