"""Tier 5: Streamlit session-state helpers."""

from __future__ import annotations

from collections.abc import Iterable

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs
    class _StreamlitStub:
        session_state: dict[str, object] = {}

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


def set_latest_models(models: Iterable[str]) -> None:
    """Persist latest model ids for display."""
    st.session_state["latest_models"] = list(models)


def get_latest_models() -> list[str]:
    """Read latest known model ids."""
    value = st.session_state.get("latest_models")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []
