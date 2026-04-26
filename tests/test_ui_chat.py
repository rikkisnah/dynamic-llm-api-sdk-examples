"""UI chat helper behavior."""

from __future__ import annotations

from dataclasses import dataclass

from llm_examples.domain_types import (
    ChatResponse,
    CheckResult,
    LLMError,
    ModelInfo,
    Usage,
)
from llm_examples.ui.helpers import (
    build_attachment_context,
    build_chat_prompt,
    build_image_attachments,
    is_image_attachment,
    normalize_uploaded_files,
    pretty_json,
    prompt_option_label,
    to_json_payload,
    wrapped_text_html,
)


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
    assert "forwarded to multimodal-capable models" in context


def test_build_image_attachments_extracts_only_images() -> None:
    files = [
        _FakeUpload(name="notes.txt", type="text/plain", payload=b"alpha"),
        _FakeUpload(name="photo.png", type="image/png", payload=b"\x89PNG"),
    ]
    images = build_image_attachments(files)
    assert len(images) == 1
    assert images[0].name == "photo.png"
    assert images[0].mime_type == "image/png"
    assert images[0].data == b"\x89PNG"


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


def test_build_chat_prompt_no_history_no_attachment() -> None:
    prompt = build_chat_prompt(
        history=[],
        user_message="Hello",
        attachment_context="",
    )
    assert "User: Hello" in prompt
    assert "Conversation so far" not in prompt
    assert "attachment" not in prompt.lower()


def test_build_chat_prompt_skips_unknown_roles() -> None:
    history = [
        {"role": "system", "content": "should be skipped"},
        {"role": "user", "content": "visible"},
    ]
    prompt = build_chat_prompt(
        history=history,
        user_message="next",
        attachment_context="",
    )
    assert "should be skipped" not in prompt
    assert "visible" in prompt


# ---------------------------------------------------------------------------
# to_json_payload
# ---------------------------------------------------------------------------


def test_to_json_payload_with_llm_error() -> None:
    error = LLMError(provider="openai", model=None, kind="auth", message="bad key")
    payload = to_json_payload(error)
    assert payload["kind"] == "auth"
    assert payload["message"] == "bad key"


def test_to_json_payload_with_chat_response() -> None:
    response = ChatResponse(
        provider="openai",
        model="gpt-4o",
        text="hello",
        latency_ms=10.0,
        usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
        raw_id="id-1",
    )
    payload = to_json_payload(response)
    assert isinstance(payload, dict)
    assert payload.get("text") == "hello"


def test_to_json_payload_with_check_result() -> None:
    result = CheckResult(provider="openai", ok=True, latency_ms=5.0, detail="ok")
    payload = to_json_payload(result)
    assert payload.get("ok") is True


def test_to_json_payload_with_model_info() -> None:
    info = ModelInfo(provider="openai", id="gpt-4o", description="latest")
    payload = to_json_payload(info)
    assert payload.get("id") == "gpt-4o"


def test_to_json_payload_with_dict() -> None:
    d = {"key": "value", "n": 42}
    payload = to_json_payload(d)
    assert payload is d


def test_to_json_payload_with_unknown_value() -> None:
    payload = to_json_payload(12345)
    assert payload == {"value": "12345"}


# ---------------------------------------------------------------------------
# pretty_json
# ---------------------------------------------------------------------------


def test_pretty_json_formats_with_indent() -> None:
    result = pretty_json({"a": 1, "b": True})
    assert '"a": 1' in result
    assert "\n" in result


# ---------------------------------------------------------------------------
# normalize_uploaded_files
# ---------------------------------------------------------------------------


def test_normalize_uploaded_files_list_of_valid() -> None:
    files = [
        _FakeUpload(name="a.txt", type="text/plain", payload=b"a"),
        _FakeUpload(name="b.png", type="image/png", payload=b"b"),
    ]
    result = normalize_uploaded_files(files)
    assert len(result) == 2


def test_normalize_uploaded_files_single_object() -> None:
    file = _FakeUpload(name="single.txt", type="text/plain", payload=b"x")
    result = normalize_uploaded_files(file)
    assert len(result) == 1
    assert result[0].name == "single.txt"


def test_normalize_uploaded_files_invalid_returns_empty() -> None:
    assert normalize_uploaded_files(None) == []
    assert normalize_uploaded_files(42) == []
    assert normalize_uploaded_files("string") == []


def test_normalize_uploaded_files_filters_invalid_items_in_list() -> None:
    valid = _FakeUpload(name="ok.txt", type="text/plain", payload=b"ok")
    result = normalize_uploaded_files(["not-a-file", None, valid])
    assert len(result) == 1
    assert result[0].name == "ok.txt"


# ---------------------------------------------------------------------------
# is_image_attachment
# ---------------------------------------------------------------------------


def test_is_image_attachment_by_mime_type() -> None:
    assert is_image_attachment(_FakeUpload(name="x", type="image/jpeg", payload=b""))
    assert not is_image_attachment(_FakeUpload(name="x", type="text/plain", payload=b""))


def test_is_image_attachment_by_extension() -> None:
    assert is_image_attachment(_FakeUpload(name="photo.png", type=None, payload=b""))
    assert is_image_attachment(_FakeUpload(name="photo.jpg", type=None, payload=b""))
    assert not is_image_attachment(_FakeUpload(name="doc.pdf", type=None, payload=b""))


# ---------------------------------------------------------------------------
# build_attachment_context - edge cases
# ---------------------------------------------------------------------------


def test_build_attachment_context_empty_returns_empty_string() -> None:
    context, names = build_attachment_context([])
    assert context == ""
    assert names == []


def test_build_attachment_context_binary_file() -> None:
    files = [_FakeUpload(name="data.bin", type="application/octet-stream", payload=b"\x00\x01")]
    context, names = build_attachment_context(files)
    assert names == ["data.bin"]
    assert "Binary file" in context
    assert "not forwarded" in context


def test_build_attachment_context_empty_text_file() -> None:
    files = [_FakeUpload(name="empty.txt", type="text/plain", payload=b"")]
    context, _names = build_attachment_context(files)
    assert "no decodable text" in context


def test_build_attachment_context_by_extension_no_mime() -> None:
    files = [_FakeUpload(name="notes.md", type=None, payload=b"# Header")]
    context, _names = build_attachment_context(files)
    assert "# Header" in context


# ---------------------------------------------------------------------------
# wrapped_text_html
# ---------------------------------------------------------------------------


def test_wrapped_text_html_escapes_special_chars() -> None:
    result = wrapped_text_html('<b>hello</b> & "world"')
    assert "&lt;b&gt;" in result
    assert "&amp;" in result
    assert "&quot;" in result


def test_wrapped_text_html_converts_newlines() -> None:
    result = wrapped_text_html("line one\nline two")
    assert "<br/>" in result


# ---------------------------------------------------------------------------
# prompt_option_label
# ---------------------------------------------------------------------------


def test_prompt_option_label_short_prompt() -> None:
    label = prompt_option_label("Short prompt")
    assert label == "Short prompt"


def test_prompt_option_label_long_prompt_truncated() -> None:
    long = "x" * 100
    label = prompt_option_label(long)
    assert len(label) <= 80
    assert label.endswith("...")


def test_prompt_option_label_multiline_uses_first_line() -> None:
    label = prompt_option_label("First line\nSecond line\nThird line")
    assert label == "First line"


def test_prompt_option_label_multiline_long_first_line_truncated() -> None:
    long_first = "A" * 90 + "\nSecond line"
    label = prompt_option_label(long_first)
    assert len(label) <= 80
    assert label.endswith("...")
