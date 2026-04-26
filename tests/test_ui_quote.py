"""UI quote refresh behavior."""

from __future__ import annotations

from dataclasses import dataclass

from llm_examples.ui import app as ui_app


@dataclass
class _FakeColumn:
    parent: _FakeStreamlit
    role: str

    def button(self, *_: object, **__: object) -> bool:
        return self.parent.refresh_clicked if self.role == "right" else False

    def markdown(self, *_: object, **__: object) -> None:
        self.parent.markdown_calls += 1


@dataclass
class _FakeStreamlit:
    session_state: dict[str, object]
    refresh_clicked: bool
    markdown_calls: int = 0
    rerun_calls: int = 0

    def columns(self, _spec: object) -> tuple[_FakeColumn, _FakeColumn]:
        return (_FakeColumn(self, "left"), _FakeColumn(self, "right"))

    def rerun(self) -> None:
        self.rerun_calls += 1


def test_quote_refresh_advances_without_rerun_and_preserves_page(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={"selected_page": "Chat", "quote_index": 0},
        refresh_clicked=True,
    )
    monkeypatch.setattr(ui_app, "st", fake_st)

    ui_app._render_quote()

    assert fake_st.session_state["quote_index"] == 1
    assert fake_st.session_state["selected_page"] == "Chat"
    assert fake_st.rerun_calls == 0
    assert fake_st.markdown_calls == 1
