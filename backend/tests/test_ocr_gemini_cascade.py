import numpy as np
import pytest

from stellegent.ocr.base import OCRResult
from stellegent.ocr import gemini


class FakeGeminiBackend:
    calls = []
    failures = set()

    name = "gemini"
    has_layout = False

    def __init__(self, model):
        self.model = model

    def recognize(self, _img):
        self.calls.append(self.model)
        if self.model in self.failures:
            raise RuntimeError(f"{self.model} exhausted")
        return OCRResult(
            full_text=f"text from {self.model}",
            has_layout=False,
            engine=f"gemini:{self.model}",
        )


def test_gemini_cascade_tries_models_in_order(monkeypatch):
    FakeGeminiBackend.calls = []
    FakeGeminiBackend.failures = {"gemini-3.5-flash", "gemini-2.5-flash"}
    monkeypatch.setattr(gemini, "GeminiBackend", FakeGeminiBackend)

    backend = gemini.GeminiCascadeBackend(
        ("gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite")
    )

    result = backend.recognize(np.zeros((1, 1, 3), dtype=np.uint8))

    assert result.full_text == "text from gemini-3.1-flash-lite"
    assert result.engine == "gemini:gemini-3.1-flash-lite"
    assert FakeGeminiBackend.calls == [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
    ]


def test_gemini_cascade_raises_last_error(monkeypatch):
    FakeGeminiBackend.calls = []
    FakeGeminiBackend.failures = {"a", "b"}
    monkeypatch.setattr(gemini, "GeminiBackend", FakeGeminiBackend)

    backend = gemini.GeminiCascadeBackend(("a", "b"))

    with pytest.raises(RuntimeError, match="b exhausted"):
        backend.recognize(np.zeros((1, 1, 3), dtype=np.uint8))

    assert FakeGeminiBackend.calls == ["a", "b"]
