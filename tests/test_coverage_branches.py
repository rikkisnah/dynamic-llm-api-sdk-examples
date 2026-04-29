"""Targeted branch tests to keep strict coverage at 100%."""

from __future__ import annotations

import argparse
import io
import sys
from importlib.metadata import PackageNotFoundError

import pytest

from llm_examples.capabilities import capability_by_name
from llm_examples.cli.cmd_check import handle_check
from llm_examples.cli.cmd_list import handle_list_models
from llm_examples.cli.cmd_providers import handle_providers
from llm_examples.cli.cmd_run import _resolve_prompt, handle_run
from llm_examples.cli.commands import dispatch
from llm_examples.cli.errors import emit_error
from llm_examples.cli.output import print_json, print_lines
from llm_examples.cli.parser import _add_parameter, capabilities_by_name, capability_names
from llm_examples.config import get_provider_config
from llm_examples.domain_types import ChatResponse, CheckResult, LLMError, MissingCredential, Usage
from llm_examples.services import run_prompt, stream_prompt
from tests.helpers import FakeClient


def test_capability_lookup_success_and_error() -> None:
    assert capability_by_name("run").name == "run"
    with pytest.raises(KeyError):
        capability_by_name("missing")


def test_config_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingCredential):
        get_provider_config("openai")


def test_config_provider_without_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    cfg = get_provider_config("openai")
    assert cfg.base_url is None


def test_config_gemini_uses_default_openai_compat_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_BASE_URL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    cfg = get_provider_config("gemini")
    assert cfg.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_domain_error_payloads() -> None:
    error = LLMError(provider="openai", model="m", kind="server", message="oops")
    assert error.to_dict()["message"] == "oops"
    missing = MissingCredential(provider="openai", env_var="OPENAI_API_KEY")
    assert missing.kind == "auth"


def test_output_helpers(capsys) -> None:  # type: ignore[no-untyped-def]
    print_json({"ok": True})
    print_lines(["a", "b"])
    captured = capsys.readouterr()
    assert '"ok": true' in captured.out
    assert "a\nb\n" in captured.out


def test_emit_error_json_branch(capsys) -> None:  # type: ignore[no-untyped-def]
    error = LLMError(provider="openai", model=None, kind="bad_request", message="bad")
    code = emit_error(error, json_output=True)
    captured = capsys.readouterr()
    assert code == 4
    assert '"ok": false' in captured.out


def test_dispatch_unknown_command_raises() -> None:
    args = argparse.Namespace(command="unknown", json=False)
    with pytest.raises(LLMError):
        dispatch(args)


def test_parser_helpers_and_add_parameter_error() -> None:
    parser = argparse.ArgumentParser()
    _add_parameter(
        parser,
        type(
            "P", (), {"name": "name", "type": "str", "required": False, "default": "x", "help": "h"}
        )(),
    )
    _add_parameter(
        parser,
        type(
            "P", (), {"name": "value", "type": "int", "required": False, "default": 1, "help": "h"}
        )(),
    )
    _add_parameter(
        parser,
        type(
            "P",
            (),
            {"name": "value_raw", "type": "int", "required": False, "default": None, "help": "h"},
        )(),
    )
    _add_parameter(
        parser,
        type(
            "P",
            (),
            {"name": "flag", "type": "bool", "required": False, "default": False, "help": "h"},
        )(),
    )
    _add_parameter(
        parser,
        type(
            "P",
            (),
            {"name": "flag_raw", "type": "bool", "required": False, "default": None, "help": "h"},
        )(),
    )
    _add_parameter(
        parser,
        type(
            "P",
            (),
            {
                "name": "provider",
                "type": "enum:provider",
                "required": False,
                "default": None,
                "help": "h",
            },
        )(),
    )
    assert capability_names()
    assert capabilities_by_name()["run"].name == "run"
    with pytest.raises(ValueError):
        _add_parameter(
            parser,
            type(
                "P",
                (),
                {"name": "x", "type": "bad", "required": False, "default": None, "help": "h"},
            )(),
        )


def test_config_fallback_loader_returns_false() -> None:
    from llm_examples import config as config_module

    assert config_module._fallback_load_dotenv() is False


def test_get_app_version_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from llm_examples import config as config_module

    monkeypatch.setattr(config_module, "_package_version", lambda _name: "9.9.9")
    assert config_module.get_app_version() == "9.9.9"


def test_get_app_version_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from llm_examples import config as config_module

    def raise_missing(_name: str) -> str:
        raise PackageNotFoundError("missing")

    monkeypatch.setattr(config_module, "_package_version", raise_missing)
    assert config_module.get_app_version() == "0.0.0"


def test_service_reraises_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class ErrorClient(FakeClient):
        def chat(self, req):  # type: ignore[override]
            raise LLMError(provider="openai", model=req.model, kind="auth", message="bad")

    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: ErrorClient())
    with pytest.raises(LLMError) as caught:
        run_prompt(provider="openai", prompt="hi")
    assert caught.value.kind == "auth"


def test_stream_service_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    class StreamErrorClient(FakeClient):
        def stream(self, req):  # type: ignore[override]
            raise LLMError(provider="openai", model=req.model, kind="network", message="down")

    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: StreamErrorClient())
    with pytest.raises(LLMError) as caught:
        stream_prompt(provider="openai", prompt="hi")
    assert caught.value.kind == "network"

    class StreamCrashClient(FakeClient):
        def stream(self, req):  # type: ignore[override]
            raise RuntimeError("boom")

    monkeypatch.setattr("llm_examples.services.get_client", lambda _provider: StreamCrashClient())
    with pytest.raises(LLMError) as caught2:
        stream_prompt(provider="openai", prompt="hi")
    assert caught2.value.kind == "server"


def test_cmd_check_and_list_non_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "llm_examples.cli.cmd_check.check_connection",
        lambda _provider: CheckResult(provider="openai", ok=True, latency_ms=1.2, detail="ok"),
    )
    monkeypatch.setattr(
        "llm_examples.cli.cmd_list.list_models",
        lambda _provider: [type("Model", (), {"id": "m1", "description": ""})()],
    )
    assert handle_check(argparse.Namespace(provider="openai", json=False)) == 0
    assert handle_list_models(argparse.Namespace(provider="openai", json=False)) == 0
    captured = capsys.readouterr()
    assert "openai: ok" in captured.out
    assert "m1" in captured.out


def test_cmd_check_and_list_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "llm_examples.cli.cmd_check.check_connection",
        lambda _provider: CheckResult(provider="openai", ok=True, latency_ms=1.2, detail="ok"),
    )
    monkeypatch.setattr(
        "llm_examples.cli.cmd_list.list_models",
        lambda _provider: [type("Model", (), {"id": "m1", "description": "d"})()],
    )
    assert handle_check(argparse.Namespace(provider="openai", json=True)) == 0
    assert handle_list_models(argparse.Namespace(provider="openai", json=True)) == 0
    captured = capsys.readouterr()
    assert '"latency_ms": 1.2' in captured.out
    assert '"description": "d"' in captured.out


def test_cmd_providers_non_json_with_missing(monkeypatch: pytest.MonkeyPatch, capsys) -> None:  # type: ignore[no-untyped-def]
    def fake_get_provider_config(provider: str):
        if provider == "openai":
            raise MissingCredential(provider="openai", env_var="OPENAI_API_KEY")
        return object()

    monkeypatch.setattr(
        "llm_examples.cli.cmd_providers.get_provider_config", fake_get_provider_config
    )
    assert handle_providers(argparse.Namespace(json=False)) == 0
    captured = capsys.readouterr()
    assert "openai: missing key" in captured.out


def test_cmd_run_non_json_paths(monkeypatch: pytest.MonkeyPatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "llm_examples.cli.cmd_run.run_prompt",
        lambda **_: ChatResponse(
            provider="openai",
            model="m",
            text="hello",
            latency_ms=1.0,
            usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            raw_id="id",
        ),
    )
    assert (
        handle_run(
            argparse.Namespace(
                provider="openai",
                model=None,
                prompt="hi",
                prompt_file=None,
                system=None,
                max_tokens=5,
                stream=False,
                json=False,
            )
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "latency_ms=1.0" in captured.out

    monkeypatch.setattr(
        "llm_examples.cli.cmd_run.stream_prompt",
        lambda **_: type(
            "R", (), {"provider": "openai", "model": "m", "chunks": ["a", "b"], "simulated": True}
        )(),
    )
    assert (
        handle_run(
            argparse.Namespace(
                provider="openai",
                model=None,
                prompt="hi",
                prompt_file=None,
                system=None,
                max_tokens=5,
                stream=True,
                json=False,
            )
        )
        == 0
    )
    captured2 = capsys.readouterr()
    assert "ab" in captured2.out
    assert "[simulated stream]" in captured2.out


def test_resolve_prompt_edge_cases(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    with pytest.raises(LLMError):
        _resolve_prompt("openai", "a", "b")
    with pytest.raises(LLMError):
        _resolve_prompt("openai", None, None)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("from-file", encoding="utf-8")
    assert _resolve_prompt("openai", None, str(prompt_file)) == "from-file"

    fake_stdin = io.StringIO("from-stdin")
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    assert _resolve_prompt("openai", None, "-") == "from-stdin"
