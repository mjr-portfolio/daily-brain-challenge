from pydantic import BaseModel

from app.core.config import get_settings
from app.services.generator import (
    GenerationError,
    PermanentGeminiError,
    _generate_checked,
)
from google.genai.errors import ClientError, ServerError


class _Payload(BaseModel):
    value: str


def _ok(payload: _Payload) -> None:
    if payload.value != "ok":
        raise GenerationError("checker rejected the puzzle")


def test_checker_failure_retries_same_model_immediately(monkeypatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []

    def fake_generate(prompt, schema, *, system_instruction, model):
        calls.append(model)
        if len(calls) == 1:
            return _Payload(value="bad")
        return _Payload(value="ok")

    monkeypatch.setattr("app.services.generator._generate_structured", fake_generate)
    monkeypatch.setattr("app.services.generator.time.sleep", sleeps.append)

    result = _generate_checked("prompt", _Payload, system_instruction="sys", check=_ok)

    assert result.value == "ok"
    assert calls == [get_settings().GEMINI_MODEL, get_settings().GEMINI_MODEL]
    assert sleeps == []


def test_service_error_waits_then_retries_same_model(monkeypatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []

    def fake_generate(prompt, schema, *, system_instruction, model):
        calls.append(model)
        if len(calls) == 1:
            raise ClientError(429, {"error": {"message": "slow down"}}, None)
        return _Payload(value="ok")

    monkeypatch.setattr("app.services.generator._generate_structured", fake_generate)
    monkeypatch.setattr("app.services.generator.time.sleep", sleeps.append)

    result = _generate_checked("prompt", _Payload, system_instruction="sys", check=_ok)

    assert result.value == "ok"
    assert calls == [get_settings().GEMINI_MODEL, get_settings().GEMINI_MODEL]
    assert sleeps == [13.0]


def test_repeated_service_error_waits_again_before_lite(monkeypatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []
    primary = get_settings().GEMINI_MODEL
    lite = get_settings().GEMINI_FALLBACK_MODEL

    def fake_generate(prompt, schema, *, system_instruction, model):
        calls.append(model)
        if model == primary:
            raise ServerError(503, {"error": {"message": "down"}}, None)
        return _Payload(value="ok")

    monkeypatch.setattr("app.services.generator._generate_structured", fake_generate)
    monkeypatch.setattr("app.services.generator.time.sleep", sleeps.append)

    result = _generate_checked("prompt", _Payload, system_instruction="sys", check=_ok)

    assert result.value == "ok"
    assert calls == [primary, primary, lite]
    assert sleeps == [13.0, 13.0]


def test_rejected_request_stops_without_retry_or_fallback(monkeypatch) -> None:
    calls: list[str] = []

    def fake_generate(prompt, schema, *, system_instruction, model):
        calls.append(model)
        raise ClientError(401, {"error": {"message": "bad key"}}, None)

    monkeypatch.setattr("app.services.generator._generate_structured", fake_generate)
    monkeypatch.setattr("app.services.generator.time.sleep", lambda _delay: calls.append("slept"))

    try:
        _generate_checked("prompt", _Payload, system_instruction="sys", check=_ok)
    except PermanentGeminiError:
        pass
    else:
        raise AssertionError("expected a permanent Gemini error")

    assert calls == [get_settings().GEMINI_MODEL]


def test_retry_after_header_sets_the_wait(monkeypatch) -> None:
    sleeps: list[float] = []

    class _Response:
        headers = {"retry-after": "2"}

    def fake_generate(prompt, schema, *, system_instruction, model):
        if not sleeps:
            error = ClientError(429, {"error": {"message": "slow down"}}, None)
            error.response = _Response()
            raise error
        return _Payload(value="ok")

    monkeypatch.setattr("app.services.generator._generate_structured", fake_generate)
    monkeypatch.setattr("app.services.generator.time.sleep", sleeps.append)

    _generate_checked("prompt", _Payload, system_instruction="sys", check=_ok)

    assert sleeps == [2.0]
