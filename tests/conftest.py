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


@pytest.fixture(autouse=True)
def _disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked_create_connection(*_: object, **__: object) -> socket.socket:
        raise RuntimeError("Network access is disabled in unit tests.")

    def blocked_connect(self: socket.socket, *_: object, **__: object) -> None:
        raise RuntimeError("Network access is disabled in unit tests.")

    monkeypatch.setattr(socket, "create_connection", blocked_create_connection)
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
