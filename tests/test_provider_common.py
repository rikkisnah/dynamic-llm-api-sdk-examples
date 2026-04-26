"""Tests for _common provider helpers."""

from __future__ import annotations

from typing import ClassVar

import pytest

from llm_examples.domain_types import ChatRequest, ImageAttachment
from llm_examples.providers._common import (
    anthropic_messages,
    attr,
    chunk_text,
    classify_exception,
    gemini_contents,
    mapping_value,
    model_info_list,
    normalize_usage,
    openai_compatible_messages_for_prompt,
    text_from_content,
    text_from_openai_response,
    text_from_openai_stream_event,
)

# ---------------------------------------------------------------------------
# classify_exception
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected_kind",
    [
        ("unauthorized token", "auth"),
        ("permission denied", "auth"),
        ("rate limit exceeded", "rate_limit"),
        ("too many requests", "rate_limit"),
        ("quota exceeded", "rate_limit"),
        ("badrequest: invalid model", "bad_request"),
        ("invalid request format", "bad_request"),
        ("connection timeout", "network"),
        ("network error occurred", "network"),
        ("internal server error", "server"),
        ("not support vision", "unsupported"),
        ("unsupported model", "unsupported"),
        ("does not support streaming", "unsupported"),
    ],
)
def test_classify_exception_by_message(message: str, expected_kind: str) -> None:
    exc = RuntimeError(message)
    assert classify_exception(exc) == expected_kind


def test_classify_exception_by_class_name() -> None:
    class AuthenticationError(Exception):
        pass

    exc = AuthenticationError("bad credentials")
    assert classify_exception(exc) == "auth"


def test_classify_exception_unknown_defaults_to_server() -> None:
    exc = ValueError("completely unknown error")
    assert classify_exception(exc) == "server"


# ---------------------------------------------------------------------------
# model_info_list
# ---------------------------------------------------------------------------


def test_model_info_list_normal() -> None:
    result = model_info_list("openai", ["gpt-4o", "gpt-4o-mini"])
    assert len(result) == 2
    assert result[0].id == "gpt-4o"
    assert result[0].provider == "openai"
    assert result[0].description == ""


def test_model_info_list_fallback_flag() -> None:
    result = model_info_list("claude", ["claude-3-haiku"], fallback=True)
    assert result[0].description == "fallback allowlist"


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


def test_chunk_text_basic() -> None:
    result = list(chunk_text("abcdefghij", chunk_size=3))
    assert result == ["abc", "def", "ghi", "j"]


def test_chunk_text_empty_string() -> None:
    assert list(chunk_text("")) == []


def test_chunk_text_exact_multiple() -> None:
    result = list(chunk_text("abcdef", chunk_size=2))
    assert result == ["ab", "cd", "ef"]


# ---------------------------------------------------------------------------
# attr and mapping_value
# ---------------------------------------------------------------------------


def test_attr_returns_attribute() -> None:
    class _Obj:
        x = 42

    assert attr(_Obj(), "x") == 42


def test_attr_returns_default_on_missing() -> None:
    assert attr(object(), "does_not_exist", "fallback") == "fallback"


def test_attr_returns_default_on_exception() -> None:
    class _Raises:
        @property
        def x(self) -> int:
            raise RuntimeError("broken")

    assert attr(_Raises(), "x", 99) == 99


def test_mapping_value_non_dict_returns_default() -> None:
    assert mapping_value("not a dict", "key", "default") == "default"
    assert mapping_value(None, "key", 0) == 0


def test_mapping_value_dict_hit() -> None:
    assert mapping_value({"k": "v"}, "k") == "v"


def test_mapping_value_dict_miss_returns_default() -> None:
    assert mapping_value({"a": 1}, "b", "missing") == "missing"


# ---------------------------------------------------------------------------
# normalize_usage
# ---------------------------------------------------------------------------


def test_normalize_usage_none() -> None:
    assert normalize_usage(None) is None


def test_normalize_usage_dict() -> None:
    usage = normalize_usage(
        {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    assert usage is not None
    assert usage.input_tokens == 10
    assert usage.output_tokens == 20
    assert usage.total_tokens == 30


def test_normalize_usage_object() -> None:
    class _Usage:
        prompt_tokens = 5
        completion_tokens = 15
        total_tokens = 20

    usage = normalize_usage(_Usage())
    assert usage is not None
    assert usage.input_tokens == 5
    assert usage.output_tokens == 15


def test_normalize_usage_missing_fields_returns_none_fields() -> None:
    usage = normalize_usage({})
    assert usage is not None
    assert usage.input_tokens is None
    assert usage.output_tokens is None


# ---------------------------------------------------------------------------
# text_from_content
# ---------------------------------------------------------------------------


def test_text_from_content_string() -> None:
    assert text_from_content("hello") == "hello"


def test_text_from_content_list_of_strings() -> None:
    assert text_from_content(["a", "b", "c"]) == "abc"


def test_text_from_content_list_of_dicts_with_text_key() -> None:
    content = [{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]
    assert text_from_content(content) == "hello world"


def test_text_from_content_dict_text_key() -> None:
    assert text_from_content({"text": "direct"}) == "direct"


def test_text_from_content_dict_output_text_key() -> None:
    assert text_from_content({"output_text": "out"}) == "out"


def test_text_from_content_object_with_text_attr() -> None:
    class _Obj:
        text = "from attr"

    assert text_from_content(_Obj()) == "from attr"


def test_text_from_content_empty_and_none() -> None:
    assert text_from_content("") == ""
    assert text_from_content(None) == ""
    assert text_from_content([]) == ""


# ---------------------------------------------------------------------------
# text_from_openai_response
# ---------------------------------------------------------------------------


def test_text_from_openai_response_attribute_based() -> None:
    class _Msg:
        content = "hello from attr"

    class _Choice:
        message = _Msg()

    class _Resp:
        text: ClassVar[str | None] = None
        choices: ClassVar[list[object]] = [_Choice()]

    assert text_from_openai_response(_Resp()) == "hello from attr"


def test_text_from_openai_response_dict_payload() -> None:
    response = {"choices": [{"message": {"content": "hello from dict"}}]}
    assert text_from_openai_response(response) == "hello from dict"


def test_text_from_openai_response_direct_text() -> None:
    class _Resp:
        text = "direct"

    assert text_from_openai_response(_Resp()) == "direct"


def test_text_from_openai_response_empty() -> None:
    assert text_from_openai_response({}) == ""


# ---------------------------------------------------------------------------
# text_from_openai_stream_event
# ---------------------------------------------------------------------------


def test_text_from_openai_stream_event_attribute_based() -> None:
    class _Delta:
        content = "chunk"

    class _Choice:
        delta = _Delta()

    class _Event:
        choices: ClassVar[list[object]] = [_Choice()]

    assert text_from_openai_stream_event(_Event()) == "chunk"


def test_text_from_openai_stream_event_empty_choices() -> None:
    assert text_from_openai_stream_event({"choices": []}) == ""


def test_text_from_openai_stream_event_no_delta() -> None:
    class _Choice:
        delta = None

    class _Event:
        choices: ClassVar[list[object]] = [_Choice()]

    assert text_from_openai_stream_event(_Event()) == ""


def test_text_from_openai_stream_event_dict_structured_content() -> None:
    event = {"choices": [{"delta": {"content": [{"type": "text", "text": "hi"}]}}]}
    assert text_from_openai_stream_event(event) == "hi"


# ---------------------------------------------------------------------------
# openai_compatible_messages_for_prompt
# ---------------------------------------------------------------------------


def test_openai_compatible_messages_no_system_no_images() -> None:
    messages = openai_compatible_messages_for_prompt(
        system=None, prompt="hello"
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"


def test_openai_compatible_messages_with_system() -> None:
    messages = openai_compatible_messages_for_prompt(
        system="You are helpful.", prompt="hello"
    )
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are helpful."
    assert messages[1]["role"] == "user"


def test_openai_compatible_messages_with_image() -> None:
    image = ImageAttachment(name="pic.png", mime_type="image/png", data=b"\x89PNG")
    messages = openai_compatible_messages_for_prompt(
        system=None, prompt="describe", image_attachments=(image,)
    )
    content = messages[0]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "describe"}
    assert isinstance(content[1], dict)
    assert content[1]["type"] == "image_url"


# ---------------------------------------------------------------------------
# anthropic_messages
# ---------------------------------------------------------------------------


def test_anthropic_messages_no_images() -> None:
    req = ChatRequest(provider="claude", model="claude-3-haiku", prompt="hi")
    messages = anthropic_messages(req)
    assert messages == [{"role": "user", "content": "hi"}]


def test_anthropic_messages_with_image() -> None:
    image = ImageAttachment(name="i.png", mime_type="image/png", data=b"\x89PNG")
    req = ChatRequest(
        provider="claude",
        model="claude-3-haiku",
        prompt="describe",
        image_attachments=(image,),
    )
    messages = anthropic_messages(req)
    content = messages[0]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "describe"}
    src = content[1]
    assert isinstance(src, dict)
    assert src["type"] == "image"
    source = src["source"]
    assert isinstance(source, dict)
    assert source["type"] == "base64"
    assert source["media_type"] == "image/png"


# ---------------------------------------------------------------------------
# gemini_contents
# ---------------------------------------------------------------------------


def test_gemini_contents_no_images() -> None:
    req = ChatRequest(provider="gemini", model="gemini-1.5-flash", prompt="hi")
    contents = gemini_contents(req)
    assert contents == "hi"


def test_gemini_contents_with_image() -> None:
    image = ImageAttachment(name="i.png", mime_type="image/png", data=b"\x89PNG")
    req = ChatRequest(
        provider="gemini",
        model="gemini-1.5-flash",
        prompt="describe",
        image_attachments=(image,),
    )
    contents = gemini_contents(req)
    assert isinstance(contents, list)
    first = contents[0]
    assert isinstance(first, dict)
    parts = first["parts"]
    assert isinstance(parts, list)
    assert parts[0] == {"text": "describe"}
    inline = parts[1]
    assert isinstance(inline, dict)
    assert inline["inline_data"]["mime_type"] == "image/png"
