"""CLI parser and command execution tests."""

from __future__ import annotations

import pytest

from llm_examples.domain_types import ChatResponse, LLMError, Usage
from llm_examples.services import StreamResult


def test_cli_providers_json(capsys) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    exit_code = main(["--json", "providers"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"providers"' in captured.out


def test_cli_run_json(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    fake_response = ChatResponse(
        provider="openai",
        model="model-a",
        text="hello",
        latency_ms=12.0,
        usage=Usage(input_tokens=1, output_tokens=2, total_tokens=3),
        raw_id="abc",
    )
    monkeypatch.setattr("llm_examples.cli.cmd_run.run_prompt", lambda **_: fake_response)
    exit_code = main(["--json", "run", "--provider", "openai", "--prompt", "hi"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"text": "hello"' in captured.out


def test_cli_run_stream_json(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    fake_result = StreamResult(
        provider="openai", model="model-a", chunks=["a", "b"], simulated=True
    )
    monkeypatch.setattr("llm_examples.cli.cmd_run.stream_prompt", lambda **_: fake_result)
    exit_code = main(
        ["--json", "run", "--provider", "openai", "--prompt", "hi", "--stream"],
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"simulated_stream": true' in captured.out


def test_cli_error_exit_code(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    def raise_auth(**_: object) -> ChatResponse:
        raise LLMError(
            provider="openai",
            model=None,
            kind="auth",
            message="missing key",
        )

    monkeypatch.setattr("llm_examples.cli.cmd_run.run_prompt", raise_auth)
    exit_code = main(["run", "--provider", "openai", "--prompt", "hi"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "auth: missing key" in captured.err


def test_cli_version(capsys) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    captured = capsys.readouterr()
    assert caught.value.code == 0
    assert "llm-examples" in captured.out


def test_cli_run_uses_env_default_provider_when_flag_omitted(
    monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    captured_args: dict[str, object] = {}

    def fake_run_prompt(**kwargs: object) -> ChatResponse:
        captured_args.update(kwargs)
        return ChatResponse(
            provider="claude",
            model="claude-haiku-4-5",
            text="hi",
            latency_ms=1.0,
            usage=None,
            raw_id=None,
        )

    monkeypatch.setattr("llm_examples.cli.cmd_run.run_prompt", fake_run_prompt)
    monkeypatch.setenv("AI_PROVIDER", "claude")
    exit_code = main(["--json", "run", "--prompt", "hello"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert captured_args.get("provider") == "claude"
    assert '"provider": "claude"' in out


def test_cli_list_models_uses_env_default_provider_when_flag_omitted(
    monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main

    monkeypatch.setattr(
        "llm_examples.cli.cmd_list.list_models",
        lambda provider: [type("M", (), {"id": f"{provider}-model", "description": ""})()],
    )
    monkeypatch.setenv("AI_PROVIDER", "qwen")
    exit_code = main(["list-models"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "qwen-model" in out


def test_cli_check_uses_env_default_provider_when_flag_omitted(
    monkeypatch, capsys
) -> None:  # type: ignore[no-untyped-def]
    from llm_examples.cli.main import main
    from llm_examples.domain_types import CheckResult

    monkeypatch.setattr(
        "llm_examples.cli.cmd_check.check_connection",
        lambda provider: CheckResult(provider=provider, ok=True, latency_ms=1.0, detail="ok"),
    )
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    exit_code = main(["check"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "deepseek: ok" in out
