"""UI chat helper behavior."""

from __future__ import annotations

from dataclasses import dataclass

from llm_examples.ui.helpers import build_attachment_context, build_chat_prompt


@dataclass
class _FakeUpload:
    name: str
    type: str | None
    payload: bytes

    def getvalue(self) -> bytes:
        return self.payload


def test_build_attachment_context_for_text_and_image() -> None:
    files = [
        _FakeUpload(name="notes.txt", type="text/plain", payload=b"alpha"),
        _FakeUpload(name="photo.png", type="image/png", payload=b"\x89PNG"),
    ]
    context, names = build_attachment_context(files)
    assert names == ["notes.txt", "photo.png"]
    assert "alpha" in context
    assert "text prompts only" in context


def test_build_chat_prompt_includes_history_and_attachments() -> None:
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    prompt = build_chat_prompt(
        history=history,
        user_message="Tell me more",
        attachment_context="File 'a.txt' content:\nabc",
    )
    assert "User: Hi" in prompt
    assert "Assistant: Hello" in prompt
    assert "Current message attachments" in prompt
    assert "User: Tell me more" in prompt
