"""Regression test: UI page selector ordering must remain `Chat / API / Logs`."""

from __future__ import annotations

from llm_examples.ui import app as ui_app
from llm_examples.ui import state as ui_state


def test_page_options_order_is_chat_api_logs() -> None:
    assert ui_app.PAGE_OPTIONS == ("Chat", "API", "Logs")


def test_default_page_is_chat() -> None:
    assert ui_app.DEFAULT_PAGE == "Chat"


def test_state_default_page_is_chat() -> None:
    """`get_selected_page` must default to `Chat` so first-time users land there."""
    import inspect

    sig = inspect.signature(ui_state.get_selected_page)
    default = sig.parameters["default"].default
    assert default == "Chat"
