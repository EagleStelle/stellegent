import requests

from stellegent.nlp import ollama_client


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} error", response=self
            )


def reset_ollama_client(monkeypatch):
    ollama_client._ensured_models.clear()
    monkeypatch.setattr(ollama_client, "OLLAMA_AUTO_PULL", True)
    monkeypatch.setattr(ollama_client, "OLLAMA_HOST", "http://ollama:11434")
    monkeypatch.setattr(ollama_client, "OLLAMA_MODEL", "phi3:mini")
    monkeypatch.setattr(ollama_client, "OLLAMA_PULL_TIMEOUT", 99)


def test_chat_pulls_missing_model_before_request(monkeypatch):
    reset_ollama_client(monkeypatch)
    calls = []

    def fake_get(url, timeout):
        calls.append(("get", url, None, timeout))
        return FakeResponse(payload={"models": []})

    def fake_post(url, json, timeout):
        calls.append(("post", url, json, timeout))
        if url.endswith("/api/pull"):
            return FakeResponse(payload={"status": "success"})
        return FakeResponse(payload={"message": {"content": "corrected"}})

    monkeypatch.setattr(ollama_client.requests, "get", fake_get)
    monkeypatch.setattr(ollama_client.requests, "post", fake_post)

    result = ollama_client.chat([{"role": "user", "content": "hello"}])

    assert result == "corrected"
    assert [call[1] for call in calls] == [
        "http://ollama:11434/api/tags",
        "http://ollama:11434/api/pull",
        "http://ollama:11434/api/chat",
    ]
    assert calls[1][2] == {"model": "phi3:mini", "stream": False}


def test_generate_skips_pull_when_model_is_installed(monkeypatch):
    reset_ollama_client(monkeypatch)
    calls = []

    def fake_get(url, timeout):
        calls.append(("get", url))
        return FakeResponse(payload={"models": [{"name": "phi3:mini"}]})

    def fake_post(url, json, timeout):
        calls.append(("post", url))
        return FakeResponse(payload={"response": "summary"})

    monkeypatch.setattr(ollama_client.requests, "get", fake_get)
    monkeypatch.setattr(ollama_client.requests, "post", fake_post)

    result = ollama_client.generate("summarize")

    assert result == "summary"
    assert ("post", "http://ollama:11434/api/pull") not in calls
    assert calls == [
        ("get", "http://ollama:11434/api/tags"),
        ("post", "http://ollama:11434/api/generate"),
    ]


def test_generate_retries_when_cached_model_was_removed(monkeypatch):
    reset_ollama_client(monkeypatch)
    ollama_client._ensured_models.add(("http://ollama:11434", "phi3:mini"))
    calls = []
    generate_attempts = 0

    def fake_get(url, timeout):
        calls.append(("get", url))
        return FakeResponse(payload={"models": []})

    def fake_post(url, json, timeout):
        nonlocal generate_attempts
        calls.append(("post", url))
        if url.endswith("/api/generate"):
            generate_attempts += 1
            if generate_attempts == 1:
                return FakeResponse(status_code=404, payload={"error": "missing"})
            return FakeResponse(payload={"response": "summary"})
        return FakeResponse(payload={"status": "success"})

    monkeypatch.setattr(ollama_client.requests, "get", fake_get)
    monkeypatch.setattr(ollama_client.requests, "post", fake_post)

    result = ollama_client.generate("summarize")

    assert result == "summary"
    assert calls == [
        ("post", "http://ollama:11434/api/generate"),
        ("get", "http://ollama:11434/api/tags"),
        ("post", "http://ollama:11434/api/pull"),
        ("post", "http://ollama:11434/api/generate"),
    ]
