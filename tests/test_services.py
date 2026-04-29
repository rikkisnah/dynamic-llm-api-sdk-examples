"""Service-layer behavior tests."""

from __future__ import annotations

import pytest

from llm_examples.domain_types import ImageAttachment, LLMError
from llm_examples.services import check_connection, list_models, run_prompt, stream_prompt
from tests.helpers import FakeClient


def test_run_prompt_uses_client_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(provider="openai", model="default-a")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    response = run_prompt(provider="openai", prompt="hello")
    assert response.model == "default-a"
    assert response.text == "echo:hello"


def test_run_prompt_prefers_env_override_when_no_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient(provider="openai", model="hardcoded-default")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    monkeypatch.setenv("OPENAI_MODEL", "env-model")
    response = run_prompt(provider="openai", prompt="hello")
    assert response.model == "env-model"


def test_stream_prompt_prefers_env_override_when_no_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeClient(provider="openai", model="hardcoded-default")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    monkeypatch.setenv("OPENAI_MODEL", "env-stream-model")
    result = stream_prompt(provider="openai", prompt="hello")
    assert result.model == "env-stream-model"


def test_run_prompt_passes_image_attachments(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(provider="openai", model="default-a")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    captured: dict[str, object] = {}
    original_chat = fake.chat

    def fake_chat(req):  # type: ignore[no-untyped-def]
        captured["images"] = req.image_attachments
        return original_chat(req)

    monkeypatch.setattr(fake, "chat", fake_chat)
    image = ImageAttachment(name="pic.png", mime_type="image/png", data=b"\x89PNG")
    _ = run_prompt(provider="openai", prompt="hello", image_attachments=(image,))
    images = captured.get("images")
    assert images == (image,)


def test_stream_prompt_exposes_simulated_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(provider="openai", model="default-a")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    result = stream_prompt(provider="openai", prompt="hello")
    assert result.simulated is True
    assert "".join(result.chunks) == "echo:hello"


def test_list_models(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(provider="openai", model="model-a")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    models = list_models("openai")
    assert [item.id for item in models] == ["model-a"]


def test_check_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(provider="openai", model="model-a")
    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: fake)
    result = check_connection("openai")
    assert result.ok is True
    assert result.provider == "openai"


def test_run_prompt_wraps_unknown_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenClient(FakeClient):
        def chat(self, req):  # type: ignore[override]
            raise RuntimeError("boom")

    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: BrokenClient())
    with pytest.raises(LLMError) as caught:
        run_prompt(provider="openai", prompt="hello")
    assert caught.value.kind == "server"
