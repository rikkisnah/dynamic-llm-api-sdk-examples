"""Provider adapter contract tests with parametrized provider rows."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, LLMError, Usage
from llm_examples.providers.claude_provider import ClaudeProvider
from llm_examples.providers.deepseek_provider import DeepSeekProvider
from llm_examples.providers.gemini_provider import GeminiProvider
from llm_examples.providers.oca_provider import OCAProvider
from llm_examples.providers.openai_provider import OpenAIProvider
from llm_examples.providers.qwen_provider import QwenProvider
from llm_examples.providers.zai_provider import ZAIProvider

PROVIDER_ROWS = (
    ("openai", OpenAIProvider),
    ("claude", ClaudeProvider),
    ("gemini", GeminiProvider),
    ("deepseek", DeepSeekProvider),
    ("qwen", QwenProvider),
    ("zai", ZAIProvider),
    ("oca", OCAProvider),
)

CHAT_MODEL_ROWS = (
    ("openai", OpenAIProvider, "gpt-4o-mini"),
    ("claude", ClaudeProvider, "claude-haiku-4-5"),
    ("gemini", GeminiProvider, "gemini-2.5-flash"),
    ("deepseek", DeepSeekProvider, "deepseek-chat"),
    ("qwen", QwenProvider, "qwen-plus"),
    ("zai", ZAIProvider, "glm-4.6"),
    ("oca", OCAProvider, "gpt-5.5"),
)


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_chat_success(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()
    request = ChatRequest(provider=provider_name, model=client.default_model, prompt="hello")

    def fake_chat(self, req: ChatRequest) -> ChatResponse:
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text="ok",
            latency_ms=0.0,
            usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            raw_id="id",
        )

    monkeypatch.setattr(provider_cls, "_chat_impl", fake_chat)
    response = client.chat(request)
    assert response.text == "ok"
    assert response.provider == provider_name


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_chat_auth_error(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()
    request = ChatRequest(provider=provider_name, model=client.default_model, prompt="hello")

    def fake_chat(self, req: ChatRequest) -> ChatResponse:
        raise RuntimeError("unauthorized token")

    monkeypatch.setattr(provider_cls, "_chat_impl", fake_chat)
    with pytest.raises(LLMError) as caught:
        client.chat(request)
    assert caught.value.kind == "auth"


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_chat_rate_limit_error(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()
    request = ChatRequest(provider=provider_name, model=client.default_model, prompt="hello")

    def fake_chat(self, req: ChatRequest) -> ChatResponse:
        raise RuntimeError("rate limit exceeded")

    monkeypatch.setattr(provider_cls, "_chat_impl", fake_chat)
    with pytest.raises(LLMError) as caught:
        client.chat(request)
    assert caught.value.kind == "rate_limit"


@pytest.mark.parametrize("provider_name,provider_cls,sample_model", CHAT_MODEL_ROWS)
def test_list_models_success(
    provider_name: str,
    provider_cls: type,
    sample_model: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from llm_examples.domain_types import ModelInfo

    client = provider_cls()

    def fake_list(self) -> list[ModelInfo]:
        return [ModelInfo(provider=provider_name, id=sample_model)]

    monkeypatch.setattr(provider_cls, "_list_models_impl", fake_list)
    models = client.list_models()
    assert [item.id for item in models] == [sample_model]


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_list_models_filters_non_chat_ids(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    from llm_examples.domain_types import ModelInfo

    client = provider_cls()

    def fake_list(self) -> list[ModelInfo]:
        return [
            ModelInfo(provider=provider_name, id="text-embedding-3-large"),
            ModelInfo(provider=provider_name, id="whisper-1"),
        ]

    monkeypatch.setattr(provider_cls, "_list_models_impl", fake_list)
    models = client.list_models()
    assert all(item.description == "fallback allowlist" for item in models)


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_list_models_fallback(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()

    def unsupported(self) -> list:  # type: ignore[type-arg]
        raise RuntimeError("not supported")

    monkeypatch.setattr(provider_cls, "_list_models_impl", unsupported)
    models = client.list_models()
    assert models
    assert all(item.description == "fallback allowlist" for item in models)


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_stream_success(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()
    request = ChatRequest(
        provider=provider_name, model=client.default_model, prompt="hello", stream=True
    )

    def fake_stream(self, req: ChatRequest) -> Iterable[str]:
        self.stream_is_simulated = False
        return ["a", "b"]

    monkeypatch.setattr(provider_cls, "_stream_impl", fake_stream)
    chunks = list(client.stream(request))
    assert chunks == ["a", "b"]
    assert client.stream_is_simulated is False


@pytest.mark.parametrize("provider_name,provider_cls", PROVIDER_ROWS)
def test_check_success(
    provider_name: str, provider_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = provider_cls()

    def fake_check(self, started: float) -> CheckResult:
        return CheckResult(provider=provider_name, ok=True, latency_ms=1.2, detail="ok")

    monkeypatch.setattr(provider_cls, "_check_impl", fake_check)
    result = client.check()
    assert result.ok is True
    assert result.provider == provider_name
