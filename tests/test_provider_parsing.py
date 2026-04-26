"""Provider parsing regression tests for structured/edge payload shapes."""

from __future__ import annotations

from typing import Any

import pytest

from llm_examples.domain_types import ChatRequest, LLMError
from llm_examples.providers._common import (
    text_from_content,
    text_from_openai_response,
    text_from_openai_stream_event,
)
from llm_examples.providers.gemini_provider import _extract_gemini_text
from llm_examples.providers.openai_provider import OpenAIProvider
from llm_examples.providers.zai_provider import ZAIProvider


class _Obj:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_text_from_content_handles_structured_blocks() -> None:
    content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]
    assert text_from_content(content) == "Hello world"


def test_text_from_openai_response_handles_dict_payload() -> None:
    response = {"choices": [{"message": {"content": [{"type": "text", "text": "Hello"}]}}]}
    assert text_from_openai_response(response) == "Hello"


def test_text_from_openai_stream_event_handles_dict_payload() -> None:
    event = {"choices": [{"delta": {"content": [{"type": "text", "text": "chunk"}]}}]}
    assert text_from_openai_stream_event(event) == "chunk"


def test_extract_gemini_text_falls_back_to_candidates() -> None:
    part = _Obj(text="Hello from Gemini")
    candidate = _Obj(content=_Obj(parts=[part]))
    response = _Obj(text="", candidates=[candidate])
    assert _extract_gemini_text(response) == "Hello from Gemini"


def test_openai_chat_retries_and_succeeds_on_empty_token_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAIProvider()
    calls: list[int] = []
    responses = [
        _Obj(
            choices=[_Obj(message=_Obj(content=""), finish_reason="length")],
            usage=None,
            id="id-1",
        ),
        _Obj(
            choices=[_Obj(message=_Obj(content="Hello after retry"), finish_reason="stop")],
            usage=None,
            id="id-2",
        ),
    ]

    def fake_create(**kwargs: Any) -> object:
        calls.append(int(kwargs.get("max_tokens", kwargs.get("max_completion_tokens"))))
        return responses[len(calls) - 1]

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="openai",
        model=provider.default_model,
        prompt="hello",
        max_tokens=512,
    )
    result = provider._chat_impl(request)
    assert result.text == "Hello after retry"
    assert calls == [512, 2048]


def test_openai_chat_raises_on_empty_token_limited_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAIProvider()

    def fake_create(**_: Any) -> object:
        return _Obj(
            choices=[_Obj(message=_Obj(content=""), finish_reason="length")],
            usage=None,
            id="id-1",
        )

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="openai",
        model=provider.default_model,
        prompt="hello",
        max_tokens=512,
    )
    with pytest.raises(LLMError, match="Increase max_tokens"):
        _ = provider._chat_impl(request)


def test_zai_chat_raises_on_empty_token_limited_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    response = _Obj(
        choices=[_Obj(message=_Obj(content=""), finish_reason="length")],
        usage=None,
        id="id-1",
    )
    client = _Obj(chat=_Obj(completions=_Obj(create=lambda **_: response)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai", model=provider.default_model, prompt="hello", max_tokens=32
    )
    with pytest.raises(RuntimeError, match="Increase max_tokens"):
        _ = provider._chat_impl(request)


def test_zai_chat_retries_and_succeeds_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    calls: list[int] = []
    responses = [
        _Obj(
            choices=[_Obj(message=_Obj(content=""), finish_reason="length")],
            usage=None,
            id="id-1",
        ),
        _Obj(
            choices=[_Obj(message=_Obj(content="Hello after retry"), finish_reason="stop")],
            usage=None,
            id="id-2",
        ),
    ]

    def fake_create(**kwargs: Any) -> object:
        calls.append(int(kwargs["max_tokens"]))
        return responses[len(calls) - 1]

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="hello",
        max_tokens=32,
    )
    result = provider._chat_impl(request)
    assert result.text == "Hello after retry"
    assert calls == [32, 512]


def test_zai_chat_auto_continues_when_non_empty_token_limited_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ZAIProvider()
    calls: list[dict[str, object]] = []
    responses = [
        _Obj(
            choices=[_Obj(message=_Obj(content="Part 1. "), finish_reason="length")],
            usage=None,
            id="id-1",
        ),
        _Obj(
            choices=[_Obj(message=_Obj(content="Part 2."), finish_reason="stop")],
            usage=None,
            id="id-2",
        ),
    ]

    def fake_create(**kwargs: Any) -> object:
        calls.append({"messages": kwargs["messages"], "max_tokens": kwargs["max_tokens"]})
        return responses[len(calls) - 1]

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="Explain streaming in APIs",
        max_tokens=128,
    )
    result = provider._chat_impl(request)
    assert result.text == "Part 1. Part 2."
    assert len(calls) == 2
    second_messages = calls[1]["messages"]
    assert isinstance(second_messages, list)
    assert second_messages
    last_message = second_messages[-1]
    assert isinstance(last_message, dict)
    content = last_message.get("content")
    assert isinstance(content, str)
    assert "Continue the same answer" in content


def test_zai_chat_extracts_structured_content(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    response = _Obj(
        choices=[
            _Obj(
                message=_Obj(
                    content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]
                ),
                finish_reason="stop",
            )
        ],
        usage=None,
        id="id-2",
    )
    client = _Obj(chat=_Obj(completions=_Obj(create=lambda **_: response)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai", model=provider.default_model, prompt="hello", max_tokens=128
    )
    result = provider._chat_impl(request)
    assert result.text == "Hello world"


def test_zai_chat_retries_and_succeeds_http(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    monkeypatch.setattr(provider, "_sdk_client", lambda: None)
    calls: list[int] = []
    payloads = [
        {
            "choices": [{"finish_reason": "length", "message": {"content": ""}}],
            "id": "id-1",
            "usage": None,
        },
        {
            "choices": [{"finish_reason": "stop", "message": {"content": "Hello from HTTP retry"}}],
            "id": "id-2",
            "usage": None,
        },
    ]

    class _FakeResponse:
        def __init__(self, data: dict[str, object]) -> None:
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._data

    class _FakeHttpClient:
        def __enter__(self) -> _FakeHttpClient:
            return self

        def __exit__(self, *_: object) -> bool:
            return False

        def post(self, _path: str, *, json: dict[str, object]) -> _FakeResponse:
            calls.append(int(json["max_tokens"]))
            return _FakeResponse(payloads[len(calls) - 1])

    monkeypatch.setattr(provider, "_http_client", lambda: _FakeHttpClient())
    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="hello",
        max_tokens=32,
    )
    result = provider._chat_impl(request)
    assert result.text == "Hello from HTTP retry"
    assert calls == [32, 512]


def test_zai_chat_auto_continues_when_non_empty_token_limited_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ZAIProvider()
    monkeypatch.setattr(provider, "_sdk_client", lambda: None)
    payloads = [
        {
            "choices": [{"finish_reason": "length", "message": {"content": "First part. "}}],
            "id": "id-1",
            "usage": None,
        },
        {
            "choices": [{"finish_reason": "stop", "message": {"content": "Second part."}}],
            "id": "id-2",
            "usage": None,
        },
    ]
    request_payloads: list[dict[str, object]] = []

    class _FakeResponse:
        def __init__(self, data: dict[str, object]) -> None:
            self._data = data

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._data

    class _FakeHttpClient:
        def __enter__(self) -> _FakeHttpClient:
            return self

        def __exit__(self, *_: object) -> bool:
            return False

        def post(self, _path: str, *, json: dict[str, object]) -> _FakeResponse:
            request_payloads.append(json)
            return _FakeResponse(payloads[len(request_payloads) - 1])

    monkeypatch.setattr(provider, "_http_client", lambda: _FakeHttpClient())
    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="Explain streaming in APIs",
        max_tokens=128,
    )
    result = provider._chat_impl(request)
    assert result.text == "First part. Second part."
    assert len(request_payloads) == 2
    second_messages = request_payloads[1]["messages"]
    assert isinstance(second_messages, list)
    assert second_messages
    second_user = second_messages[-1]
    assert isinstance(second_user, dict)
    content = second_user.get("content")
    assert isinstance(content, str)
    assert "Continue the same answer" in content


def test_zai_stream_extracts_structured_delta_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    events = [
        {"choices": [{"delta": {"content": [{"type": "text", "text": "Hello"}]}}]},
        {"choices": [{"delta": {"content": " world"}}]},
    ]

    def fake_create(**kwargs: Any) -> object:
        if kwargs.get("stream"):
            return events
        return _Obj(choices=[], usage=None, id="id-3")

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="hello",
        max_tokens=128,
        stream=True,
    )
    chunks = list(provider._stream_impl(request))
    assert chunks == ["Hello", " world"]
    assert provider.stream_is_simulated is False


def test_zai_stream_auto_continues_when_token_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ZAIProvider()
    prompts: list[str] = []
    first_events = [
        {"choices": [{"delta": {"content": "Part 1 "}}]},
        {"choices": [{"delta": {"content": "Part 2"}}]},
        {"choices": [{"delta": {}, "finish_reason": "length"}]},
    ]
    second_events = [
        {"choices": [{"delta": {"content": " and Part 3"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ]

    def fake_create(**kwargs: Any) -> object:
        messages = kwargs.get("messages")
        if isinstance(messages, list) and messages and isinstance(messages[-1], dict):
            content = messages[-1].get("content")
            if isinstance(content, str):
                prompts.append(content)
        if kwargs.get("stream"):
            return first_events if len(prompts) == 1 else second_events
        return _Obj(choices=[], usage=None, id="id-3")

    client = _Obj(chat=_Obj(completions=_Obj(create=fake_create)))
    monkeypatch.setattr(provider, "_sdk_client", lambda: client)

    request = ChatRequest(
        provider="zai",
        model=provider.default_model,
        prompt="Explain streaming in APIs",
        max_tokens=128,
        stream=True,
    )
    chunks = list(provider._stream_impl(request))
    assert "".join(chunks) == "Part 1 Part 2 and Part 3"
    assert len(prompts) == 2
    assert "Continue the same answer" in prompts[1]
