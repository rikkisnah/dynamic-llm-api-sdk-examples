"""UI session-state helpers for chat memory."""

from __future__ import annotations

from dataclasses import dataclass

from llm_examples.ui import state as ui_state


@dataclass
class _FakeStreamlit:
    session_state: dict[str, object]


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_selected_provider_persists(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    assert ui_state.get_selected_provider("openai") == "openai"
    ui_state.set_selected_provider("claude")
    assert ui_state.get_selected_provider("openai") == "claude"


def test_selected_provider_default_written_to_state(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    result = ui_state.get_selected_provider("gemini")
    assert result == "gemini"
    assert fake_st.session_state.get("selected_provider") == "gemini"


# ---------------------------------------------------------------------------
# Output mode
# ---------------------------------------------------------------------------


def test_output_mode_default_txt(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    assert ui_state.get_output_mode() == "txt"


def test_output_mode_persists_valid_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.set_output_mode("json")
    assert ui_state.get_output_mode() == "json"


def test_output_mode_ignores_invalid_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.set_output_mode("txt")
    ui_state.set_output_mode("bad-mode")  # should be silently ignored
    assert ui_state.get_output_mode() == "txt"


# ---------------------------------------------------------------------------
# Latest models per provider
# ---------------------------------------------------------------------------


def test_latest_models_scoped_per_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.set_latest_models("openai", ["gpt-4o", "gpt-4o-mini"])
    ui_state.set_latest_models("claude", ["claude-3-haiku"])

    assert ui_state.get_latest_models("openai") == ["gpt-4o", "gpt-4o-mini"]
    assert ui_state.get_latest_models("claude") == ["claude-3-haiku"]
    assert ui_state.get_latest_models("gemini") == []


def test_latest_models_overwrites_existing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.set_latest_models("openai", ["gpt-4o"])
    ui_state.set_latest_models("openai", ["gpt-5", "gpt-5-mini"])
    assert ui_state.get_latest_models("openai") == ["gpt-5", "gpt-5-mini"]


# ---------------------------------------------------------------------------
# UI call log
# ---------------------------------------------------------------------------


def test_ui_call_log_append_and_read(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    assert ui_state.get_ui_call_log() == []
    ui_state.append_ui_call_log({"provider": "openai", "status": "ok"})
    ui_state.append_ui_call_log({"provider": "claude", "status": "error"})

    log = ui_state.get_ui_call_log()
    assert len(log) == 2
    # most recent first
    assert log[0]["provider"] == "claude"
    assert log[1]["provider"] == "openai"


def test_ui_call_log_clear(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.append_ui_call_log({"x": 1})
    ui_state.clear_ui_call_log()
    assert ui_state.get_ui_call_log() == []


def test_ui_call_log_bounded_to_200(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    for i in range(210):
        ui_state.append_ui_call_log({"n": i})

    assert len(ui_state.get_ui_call_log()) == 200


# ---------------------------------------------------------------------------
# Chat model selection
# ---------------------------------------------------------------------------


def test_get_selected_chat_model_empty_options_returns_empty_string(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    assert ui_state.get_selected_chat_model("openai", []) == ""


def test_get_selected_chat_model_returns_fallback_when_stored_not_in_options(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.set_selected_chat_model("openai", "old-model")
    # old-model is not in the current options list
    result = ui_state.get_selected_chat_model("openai", ["gpt-4o", "gpt-5"])
    assert result == "gpt-4o"


# ---------------------------------------------------------------------------
# Chat history bounded
# ---------------------------------------------------------------------------


def test_chat_history_bounded_to_60_messages(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    for i in range(70):
        role = "user" if i % 2 == 0 else "assistant"
        ui_state.append_chat_message("openai", "gpt-4o", role, f"msg {i}")

    messages = ui_state.get_chat_messages("openai", "gpt-4o")
    assert len(messages) == 60


# ---------------------------------------------------------------------------
# Prompt history edge cases
# ---------------------------------------------------------------------------


def test_add_prompt_history_empty_scope_is_no_op(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.add_prompt_history("", "hello")
    assert ui_state.get_prompt_history("") == []


def test_add_prompt_history_empty_prompt_is_no_op(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    ui_state.add_prompt_history("run:openai", "   ")
    assert ui_state.get_prompt_history("run:openai") == []


def test_clear_prompt_history_empty_scope_is_no_op(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_state, "st", fake_st)

    # Should not raise
    ui_state.clear_prompt_history("   ")


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
