"""UI run-form regression tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from llm_examples.domain_types import ModelInfo
from llm_examples.ui import app as ui_app


@dataclass
class _FakeForm:
    def __enter__(self) -> _FakeForm:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> bool:
        return False


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.selected_model_options: list[str] | None = None
        self.warning_messages: list[str] = []

    def subheader(self, *_: object, **__: object) -> None:
        return None

    def warning(self, message: str, **__: object) -> None:
        self.warning_messages.append(message)

    def columns(self, _count: object) -> tuple[_FakeStreamlit, _FakeStreamlit]:
        return (self, self)

    def form(self, _name: str) -> _FakeForm:
        return _FakeForm()

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        index: int = 0,
        help: str | None = None,
        **__: object,
    ) -> str:
        del help
        self.selected_model_options = list(options)
        return options[index]

    def text_area(self, _label: str, **__: object) -> str:
        return ""

    def text_input(self, _label: str, **__: object) -> str:
        return ""

    def number_input(self, _label: str, **__: object) -> int:
        return 64

    def checkbox(self, _label: str, **__: object) -> bool:
        return False

    def form_submit_button(self, _label: str, **__: object) -> bool:
        return False

    def button(self, _label: str, **__: object) -> bool:
        return False


def test_run_form_models_fetched_from_provider_list(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_app, "st", fake_st)
    monkeypatch.setattr(ui_app, "get_latest_models", lambda _provider: [])
    monkeypatch.setattr(ui_app, "get_prompt_history", lambda _scope: [])
    monkeypatch.setattr(ui_app, "clear_prompt_history", lambda _scope: None)

    models = [
        ModelInfo(provider="openai", id="gpt-4o-mini"),
        ModelInfo(provider="openai", id="gpt-4.1-mini"),
    ]
    monkeypatch.setattr(ui_app, "list_models", lambda _provider: models)

    captured = SimpleNamespace(provider="", models=list[str]())

    def _capture_set_latest_models(provider: str, latest: list[str]) -> None:
        captured.provider = provider
        captured.models = list(latest)

    monkeypatch.setattr(ui_app, "set_latest_models", _capture_set_latest_models)

    ui_app._render_run("openai", "txt")

    assert fake_st.selected_model_options == ["gpt-4o-mini", "gpt-4.1-mini"]
    assert captured.provider == "openai"
    assert captured.models == ["gpt-4o-mini", "gpt-4.1-mini"]


def test_run_form_models_use_provider_scoped_cache(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_app, "st", fake_st)
    monkeypatch.setattr(ui_app, "get_latest_models", lambda _provider: ["qwen-plus"])
    monkeypatch.setattr(ui_app, "get_prompt_history", lambda _scope: [])
    monkeypatch.setattr(ui_app, "clear_prompt_history", lambda _scope: None)

    def _should_not_call(_provider: str) -> list[ModelInfo]:
        raise AssertionError("list_models should not be called when cache is available")

    monkeypatch.setattr(ui_app, "list_models", _should_not_call)
    monkeypatch.setattr(ui_app, "set_latest_models", lambda _provider, _models: None)

    ui_app._render_run("qwen", "txt")

    assert fake_st.selected_model_options == ["qwen-plus"]
    assert not fake_st.warning_messages
