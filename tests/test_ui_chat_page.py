"""Tests for chat_page pure-logic helpers."""

from __future__ import annotations

import pytest

from llm_examples.domain_types import LLMError
from llm_examples.ui import state as ui_state
from llm_examples.ui.chat_page import (
    _load_provider_model_options,
    _prompt_history_scope_for_chat,
    _should_scroll_response,
)
from llm_examples.ui.state import set_latest_models


class _FakeSt:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}


# ---------------------------------------------------------------------------
# _prompt_history_scope_for_chat
# ---------------------------------------------------------------------------


def test_prompt_history_scope_format() -> None:
    scope = _prompt_history_scope_for_chat("openai", "gpt-4o")
    assert scope == "chat:openai:gpt-4o"


def test_prompt_history_scope_unique_per_model() -> None:
    assert _prompt_history_scope_for_chat("openai", "gpt-4o") != _prompt_history_scope_for_chat(
        "openai", "gpt-5"
    )


# ---------------------------------------------------------------------------
# _should_scroll_response
# ---------------------------------------------------------------------------


def test_should_scroll_response_long_text() -> None:
    assert _should_scroll_response("x" * 2500) is True


def test_should_scroll_response_many_lines() -> None:
    content = "\n".join(f"line {i}" for i in range(30))
    assert _should_scroll_response(content) is True


def test_should_scroll_response_short_text() -> None:
    assert _should_scroll_response("short text") is False


def test_should_scroll_response_exactly_at_char_threshold() -> None:
    # threshold is >= 2000 chars
    assert _should_scroll_response("x" * 1999) is False
    assert _should_scroll_response("x" * 2000) is True


def test_should_scroll_response_exactly_at_line_threshold() -> None:
    just_under = "\n".join(f"L{i}" for i in range(23))
    just_over = "\n".join(f"L{i}" for i in range(24))
    assert _should_scroll_response(just_under) is False
    assert _should_scroll_response(just_over) is True


# ---------------------------------------------------------------------------
# _load_provider_model_options
# ---------------------------------------------------------------------------


def test_load_provider_model_options_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_st = _FakeSt()
    monkeypatch.setattr(ui_state, "st", fake_st)
    set_latest_models("openai", ["gpt-4o", "gpt-5"])

    def _should_not_call(_provider: str) -> list:
        raise AssertionError("list_models should not be called when cache is present")

    monkeypatch.setattr("llm_examples.ui.chat_page.list_models", _should_not_call)

    result = _load_provider_model_options("openai")
    assert result == ["gpt-4o", "gpt-5"]


def test_load_provider_model_options_fetches_when_cache_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from llm_examples.domain_types import ModelInfo

    fake_st = _FakeSt()
    monkeypatch.setattr(ui_state, "st", fake_st)

    fake_models = [
        ModelInfo(provider="openai", id="gpt-4o"),
        ModelInfo(provider="openai", id="gpt-5"),
    ]
    monkeypatch.setattr("llm_examples.ui.chat_page.list_models", lambda _: fake_models)
    monkeypatch.setattr("llm_examples.ui.chat_page.set_latest_models", lambda _p, _m: None)

    result = _load_provider_model_options("openai")
    assert result == ["gpt-4o", "gpt-5"]


def test_load_provider_model_options_returns_empty_on_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_st = _FakeSt()
    monkeypatch.setattr(ui_state, "st", fake_st)

    def raise_error(_provider: str) -> list:
        raise LLMError(
            provider="openai", model=None, kind="auth", message="missing key"
        )

    monkeypatch.setattr("llm_examples.ui.chat_page.list_models", raise_error)

    result = _load_provider_model_options("openai")
    assert result == []
