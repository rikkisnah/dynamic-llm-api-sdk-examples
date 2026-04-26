"""Tier 5: UI formatting helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from html import escape
from typing import Protocol, TypeGuard

from llm_examples.domain_types import (
    ChatResponse,
    CheckResult,
    ImageAttachment,
    LLMError,
    ModelInfo,
)


def to_json_payload(value: object) -> Mapping[str, object]:
    """Convert known response objects into JSON-friendly mappings."""
    if isinstance(value, LLMError):
        return dict(value.to_dict())
    if isinstance(value, ChatResponse):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, CheckResult):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, ModelInfo):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def pretty_json(payload: Mapping[str, object]) -> str:
    """Render stable JSON for Streamlit code blocks."""
    return json.dumps(payload, indent=2)


TEXT_ATTACHMENT_SUFFIXES = (
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".log",
    ".xml",
    ".html",
    ".py",
    ".js",
    ".ts",
)
IMAGE_ATTACHMENT_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
MAX_CHAT_HISTORY_CHARS = 12_000
MAX_ATTACHMENT_CHARS = 6_000


class UploadedFileLike(Protocol):
    name: str
    type: str | None

    def getvalue(self) -> bytes:
        ...


def _is_uploaded_file_like(value: object) -> TypeGuard[UploadedFileLike]:
    name = getattr(value, "name", None)
    getter = getattr(value, "getvalue", None)
    return isinstance(name, str) and callable(getter)


def normalize_uploaded_files(value: object) -> list[UploadedFileLike]:
    """Normalize uploader value to a list of uploaded-file-like objects."""
    if isinstance(value, list):
        return [item for item in value if _is_uploaded_file_like(item)]
    if _is_uploaded_file_like(value):
        return [value]
    return []


def _is_text_attachment(file: UploadedFileLike) -> bool:
    mime = (file.type or "").lower()
    if mime.startswith("text/"):
        return True
    return file.name.lower().endswith(TEXT_ATTACHMENT_SUFFIXES)


def _is_image_attachment(file: UploadedFileLike) -> bool:
    mime = (file.type or "").lower()
    if mime.startswith("image/"):
        return True
    return file.name.lower().endswith(IMAGE_ATTACHMENT_SUFFIXES)


def is_image_attachment(file: UploadedFileLike) -> bool:
    """Return whether uploaded file is image-like."""
    return _is_image_attachment(file)


def build_image_attachments(
    uploaded_files: Sequence[UploadedFileLike],
) -> tuple[ImageAttachment, ...]:
    """Build image payloads for multimodal provider requests."""
    rows: list[ImageAttachment] = []
    for file in uploaded_files:
        if not _is_image_attachment(file):
            continue
        file_name = file.name.strip() or "uploaded-image"
        mime = (file.type or "").strip().lower() or "image/png"
        rows.append(ImageAttachment(name=file_name, mime_type=mime, data=file.getvalue()))
    return tuple(rows)


def build_attachment_context(uploaded_files: Sequence[UploadedFileLike]) -> tuple[str, list[str]]:
    """Build textual context summary from uploaded files."""
    if not uploaded_files:
        return "", []
    sections: list[str] = []
    names: list[str] = []
    for file in uploaded_files:
        data = file.getvalue()
        file_name = file.name.strip() or "uploaded-file"
        mime = (file.type or "application/octet-stream").strip()
        names.append(file_name)
        if _is_text_attachment(file):
            text = data.decode("utf-8", errors="ignore").strip()
            excerpt = text[:MAX_ATTACHMENT_CHARS]
            if excerpt:
                sections.append(f"File '{file_name}' content:\n{excerpt}")
            else:
                sections.append(f"File '{file_name}' was uploaded but had no decodable text.")
            continue
        if _is_image_attachment(file):
            sections.append(
                f"Image '{file_name}' attached ({mime}, {len(data)} bytes). "
                "Image data is forwarded to multimodal-capable models."
            )
            continue
        sections.append(
            f"Binary file '{file_name}' uploaded ({mime}, {len(data)} bytes). "
            "Binary content is not forwarded to this text-only chat API."
        )
    return "\n\n".join(sections), names


def _history_as_prompt(messages: Sequence[dict[str, str]]) -> str:
    blocks: list[str] = []
    total_chars = 0
    for message in reversed(messages):
        role = message.get("role", "")
        content = message.get("content", "").strip()
        if not content:
            continue
        if role == "assistant":
            prefix = "Assistant"
        elif role == "user":
            prefix = "User"
        else:
            continue
        block = f"{prefix}: {content}"
        projected = total_chars + len(block)
        if projected > MAX_CHAT_HISTORY_CHARS and blocks:
            break
        blocks.append(block)
        total_chars = projected
    blocks.reverse()
    return "\n\n".join(blocks)


def build_chat_prompt(
    *,
    history: Sequence[dict[str, str]],
    user_message: str,
    attachment_context: str,
) -> str:
    """Build a single prompt string from chat history and current turn."""
    sections = ["Continue this chat naturally and answer the latest user request."]
    history_text = _history_as_prompt(history)
    if history_text:
        sections.append(f"Conversation so far:\n{history_text}")
    if attachment_context:
        sections.append(f"Current message attachments:\n{attachment_context}")
    sections.append(f"User: {user_message}")
    sections.append("Assistant:")
    return "\n\n".join(sections)


def wrapped_text_html(text: str) -> str:
    """Render safe wrapped text HTML for chat bubbles."""
    safe = escape(text).replace("\n", "<br/>")
    return f"<div class='chat-wrap'>{safe}</div>"


def prompt_option_label(prompt: str) -> str:
    """Render one-line label for saved prompt selector."""
    first_line = prompt.splitlines()[0] if "\n" in prompt else prompt
    normalized = first_line.strip()
    if len(normalized) <= 80:
        return normalized
    return normalized[:77] + "..."
