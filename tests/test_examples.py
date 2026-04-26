"""Standalone example script tests with mocked SDK paths."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_example_module(script_name: str) -> ModuleType:
    path = ROOT / "examples" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "script_name,env_name,patcher",
    [
        (
            "openai_example.py",
            "OPENAI_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt", lambda *_: "ok"),
            ),
        ),
        (
            "deepseek_example.py",
            "DEEPSEEK_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt", lambda *_: "ok"),
            ),
        ),
        (
            "claude_example.py",
            "ANTHROPIC_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt", lambda *_: "ok"),
            ),
        ),
        (
            "gemini_example.py",
            "GEMINI_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt", lambda *_: "ok"),
            ),
        ),
        (
            "qwen_example.py",
            "DASHSCOPE_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt", lambda *_: "ok"),
            ),
        ),
        (
            "zai_example.py",
            "ZAI_API_KEY",
            lambda module, monkeypatch: (
                monkeypatch.setattr(module, "build_sdk_client", lambda *_: object()),
                monkeypatch.setattr(module, "list_models", lambda *_: ["model-a"]),
                monkeypatch.setattr(module, "run_prompt_sdk", lambda *_: "ok"),
                monkeypatch.setattr(module, "run_prompt_http", lambda *_: "ok"),
            ),
        ),
    ],
)
def test_example_main(
    script_name: str, env_name: str, patcher, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_example_module(script_name)
    monkeypatch.setenv(env_name, "test-key")
    patcher(module, monkeypatch)
    assert module.main() == 0
