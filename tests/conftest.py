"""Pytest fixtures for environment setup and network isolation."""

from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def _set_test_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-dashscope-key")
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.setenv("OCA_API_KEY", "test-oca-key")
    # Disable on-disk UI persistence so unit tests stay hermetic.
    monkeypatch.setenv("LLM_EXAMPLES_DISABLE_STATE", "1")
    # Reset provider/model selectors so tests start from a clean default.
    for name in (
        "AI_PROVIDER",
        "DEFAULT_AI_PROVIDER",
        "AI_MODEL",
        "AI_MAX_TOKENS",
        "MAX_TOKENS",
        "OPENAI_MODEL",
        "OPENAI_MODEL_CHAT",
        "ANTHROPIC_MODEL",
        "CLAUDE_MODEL",
        "CLAUDE_CHAT_MODEL",
        "GEMINI_MODEL",
        "DEEPSEEK_MODEL",
        "QWEN_MODEL",
        "DASHSCOPE_MODEL",
        "ZAI_MODEL",
        "Z_AI_MODEL",
        "OCA_MODEL",
        "MODEL_CHAT",
        "REASONING_EFFORT",
        "OCA_BASE_URL",
        "GEMINI_BASE_URL",
        "OCA_ACCESS_TOKEN",
        "CODEX_AUTH_PATH",
        "OCA_CLIENT_HEADER",
        "OCA_CLIENT_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked_create_connection(*_: object, **__: object) -> socket.socket:
        raise RuntimeError("Network access is disabled in unit tests.")

    def blocked_connect(self: socket.socket, *_: object, **__: object) -> None:
        raise RuntimeError("Network access is disabled in unit tests.")

    monkeypatch.setattr(socket, "create_connection", blocked_create_connection)
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
