"""UI session-state helpers for chat memory."""

from __future__ import annotations

from dataclasses import dataclass

from llm_examples.ui import state as ui_state


@dataclass
class _FakeStreamlit:
    session_state: dict[str, object]


def test_selected_chat_model_persists_per_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    selected = ui_state.get_selected_chat_model("openai", ["gpt-4o-mini", "gpt-5-mini"])
    assert selected == "gpt-4o-mini"
    ui_state.set_selected_chat_model("openai", "gpt-5-mini")
    assert ui_state.get_selected_chat_model("openai", ["gpt-4o-mini", "gpt-5-mini"]) == "gpt-5-mini"


def test_selected_page_persists(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    assert ui_state.get_selected_page("API") == "API"
    ui_state.set_selected_page("Chat")
    assert ui_state.get_selected_page("API") == "Chat"


def test_chat_messages_are_scoped_and_clearable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.append_chat_message("openai", "gpt-4o-mini", "user", "hello")
    ui_state.append_chat_message("openai", "gpt-4o-mini", "assistant", "hi")
    ui_state.append_chat_message("openai", "gpt-5-mini", "user", "other thread")

    first_thread = ui_state.get_chat_messages("openai", "gpt-4o-mini")
    second_thread = ui_state.get_chat_messages("openai", "gpt-5-mini")

    assert [item["role"] for item in first_thread] == ["user", "assistant"]
    assert second_thread == [{"role": "user", "content": "other thread"}]

    ui_state.clear_chat_messages("openai", "gpt-4o-mini")
    assert ui_state.get_chat_messages("openai", "gpt-4o-mini") == []
    assert ui_state.get_chat_messages("openai", "gpt-5-mini") == second_thread


def test_prompt_history_scoped_deduped_and_clearable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.add_prompt_history("run:openai", "hello")
    ui_state.add_prompt_history("run:openai", "world")
    ui_state.add_prompt_history("run:openai", "hello")
    ui_state.add_prompt_history("chat:openai:gpt-5-mini", "what is mauritius")

    run_history = ui_state.get_prompt_history("run:openai")
    chat_history = ui_state.get_prompt_history("chat:openai:gpt-5-mini")

    assert run_history == ["hello", "world"]
    assert chat_history == ["what is mauritius"]

    ui_state.clear_prompt_history("run:openai")
    assert ui_state.get_prompt_history("run:openai") == []
    assert ui_state.get_prompt_history("chat:openai:gpt-5-mini") == ["what is mauritius"]
