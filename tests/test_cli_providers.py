"""Coverage for the CLI provider-resolution helper."""

from __future__ import annotations

import pytest

from llm_examples.cli.providers import resolve_provider


def test_resolve_provider_passes_through_explicit_value() -> None:
    assert resolve_provider("claude") == "claude"


def test_resolve_provider_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "z.ai")
    assert resolve_provider(None) == "zai"


def test_resolve_provider_uses_compiled_default_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("DEFAULT_AI_PROVIDER", raising=False)
    assert resolve_provider(None) == "openai"
