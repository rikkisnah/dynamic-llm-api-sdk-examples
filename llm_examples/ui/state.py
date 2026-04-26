"""Tier 5: Streamlit session-state helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import ClassVar, Literal

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs

    class _StreamlitStub:
        session_state: ClassVar[dict[str, object]] = {}

    st = _StreamlitStub()  # type: ignore[assignment]


def get_selected_provider(default: str) -> str:
    """Read selected provider from session state."""
    value = st.session_state.get("selected_provider")
    if isinstance(value, str) and value:
        return value
    st.session_state["selected_provider"] = default
    return default


def set_selected_provider(value: str) -> None:
    """Persist selected provider in session state."""
    st.session_state["selected_provider"] = value


def get_output_mode(default: str = "txt") -> str:
    """Read selected output mode from session state."""
    value = st.session_state.get("output_mode")
    if isinstance(value, str) and value in {"txt", "json"}:
        return value
    st.session_state["output_mode"] = default
    return default


def set_output_mode(value: str) -> None:
    """Persist output mode in session state."""
    if value in {"txt", "json"}:
        st.session_state["output_mode"] = value


def _get_models_by_provider() -> dict[str, list[str]]:
    value = st.session_state.get("latest_models_by_provider")
    if not isinstance(value, dict):
        return {}
    rows: dict[str, list[str]] = {}
    for key, raw_models in value.items():
        if not isinstance(key, str) or not isinstance(raw_models, list):
            continue
        rows[key] = [item for item in raw_models if isinstance(item, str)]
    return rows


def set_latest_models(provider: str, models: Iterable[str]) -> None:
    """Persist latest model ids for one provider."""
    rows = _get_models_by_provider()
    rows[provider] = [item for item in models if isinstance(item, str)]
    st.session_state["latest_models_by_provider"] = rows


def get_latest_models(provider: str) -> list[str]:
    """Read latest known model ids for one provider."""
    return _get_models_by_provider().get(provider, [])


def _get_selected_chat_models() -> dict[str, str]:
    value = st.session_state.get("selected_chat_model_by_provider")
    if not isinstance(value, dict):
        return {}
    rows: dict[str, str] = {}
    for key, model in value.items():
        if isinstance(key, str) and isinstance(model, str):
            rows[key] = model
    return rows


def set_selected_chat_model(provider: str, model: str) -> None:
    """Persist selected chat model per provider."""
    rows = _get_selected_chat_models()
    rows[provider] = model
    st.session_state["selected_chat_model_by_provider"] = rows


def get_selected_chat_model(provider: str, options: list[str]) -> str:
    """Read selected chat model for provider or initialize from model options."""
    rows = _get_selected_chat_models()
    selected = rows.get(provider)
    if isinstance(selected, str) and selected in options:
        return selected
    if options:
        fallback = options[0]
        rows[provider] = fallback
        st.session_state["selected_chat_model_by_provider"] = rows
        return fallback
    return ""


ChatRole = Literal["user", "assistant"]


def _chat_thread_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def _get_chat_threads() -> dict[str, list[dict[str, str]]]:
    value = st.session_state.get("chat_threads")
    if not isinstance(value, dict):
        return {}
    rows: dict[str, list[dict[str, str]]] = {}
    for key, raw_thread in value.items():
        if not isinstance(key, str) or not isinstance(raw_thread, list):
            continue
        thread: list[dict[str, str]] = []
        for item in raw_thread:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                thread.append({"role": role, "content": content})
        rows[key] = thread
    return rows


def get_chat_messages(provider: str, model: str) -> list[dict[str, str]]:
    """Read chat history for one provider+model thread."""
    key = _chat_thread_key(provider, model)
    return _get_chat_threads().get(key, [])


def append_chat_message(provider: str, model: str, role: ChatRole, content: str) -> None:
    """Append one chat turn and keep a bounded history per provider+model."""
    rows = _get_chat_threads()
    key = _chat_thread_key(provider, model)
    thread = list(rows.get(key, []))
    thread.append({"role": role, "content": content})
    rows[key] = thread[-60:]
    st.session_state["chat_threads"] = rows


def clear_chat_messages(provider: str, model: str) -> None:
    """Clear chat history for one provider+model thread."""
    rows = _get_chat_threads()
    key = _chat_thread_key(provider, model)
    rows[key] = []
    st.session_state["chat_threads"] = rows


def append_ui_call_log(entry: Mapping[str, object]) -> None:
    """Append one UI call log entry and keep a bounded history."""
    value = st.session_state.get("ui_call_log")
    logs = [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    logs.insert(0, dict(entry))
    st.session_state["ui_call_log"] = logs[:200]


def get_ui_call_log() -> list[dict[str, object]]:
    """Read current UI call logs from session state."""
    value = st.session_state.get("ui_call_log")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def clear_ui_call_log() -> None:
    """Clear UI call log history."""
    st.session_state["ui_call_log"] = []


PROMPT_HISTORY_LIMIT = 20


def _get_prompt_history_store() -> dict[str, list[str]]:
    value = st.session_state.get("prompt_history")
    if not isinstance(value, dict):
        return {}
    rows: dict[str, list[str]] = {}
    for key, raw_history in value.items():
        if not isinstance(key, str) or not isinstance(raw_history, list):
            continue
        rows[key] = [item for item in raw_history if isinstance(item, str)]
    return rows


def get_prompt_history(scope: str) -> list[str]:
    """Read recent prompt values for one UI scope."""
    if not scope:
        return []
    return _get_prompt_history_store().get(scope, [])


def add_prompt_history(scope: str, prompt: str) -> None:
    """Append one prompt to scope history with dedupe and bounded size."""
    cleaned_scope = scope.strip()
    cleaned_prompt = prompt.strip()
    if not cleaned_scope or not cleaned_prompt:
        return
    rows = _get_prompt_history_store()
    history = [item for item in rows.get(cleaned_scope, []) if item != cleaned_prompt]
    history.insert(0, cleaned_prompt)
    rows[cleaned_scope] = history[:PROMPT_HISTORY_LIMIT]
    st.session_state["prompt_history"] = rows


def clear_prompt_history(scope: str) -> None:
    """Clear prompt history for one scope."""
    cleaned_scope = scope.strip()
    if not cleaned_scope:
        return
    rows = _get_prompt_history_store()
    rows[cleaned_scope] = []
    st.session_state["prompt_history"] = rows
