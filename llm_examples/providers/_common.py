"""Tier 2: Shared provider adapter helpers."""

from __future__ import annotations

import base64
import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from contextlib import suppress
from typing import Literal, cast

from llm_examples.config import explicit_provider_model
from llm_examples.domain_types import (
    ChatRequest,
    ChatResponse,
    CheckResult,
    ImageAttachment,
    LLMError,
    ModelInfo,
    ProviderName,
    Usage,
)
from llm_examples.llm_client import BaseClient

logger = logging.getLogger(__name__)

_NOT_SUPPORTED_HINTS = ("not support", "unsupported", "not implemented", "does not support")

RETRY_MIN_MAX_TOKENS = 512
RETRY_MAX_MAX_TOKENS = 4096

_NON_CHAT_MARKERS: tuple[str, ...] = (
    "embedding",
    "embed",
    "rerank",
    "moderation",
    "whisper",
    "tts",
    "transcribe",
    "speech",
    "image",
    "vision-preview",
    "audio",
    "realtime",
    "babbage",
    "davinci",
    "customtools",
    "thinking",
    "thought",
    "reasoner",
    "computer-use",
    "computer_use",
)

# Stable Gemini families that work via the OpenAI-compatible endpoint with
# standard tool calling. Specialty variants (computer-use, customtools,
# thinking, image-generation, native-audio, gemini-3.x preview, etc.) require
# Google-native plumbing the OpenAI-compatible protocol cannot supply, so we
# allowlist instead of blocklist.
_GEMINI_STABLE_RE = re.compile(
    r"^gemini-(?:1\.5|2\.0|2\.5)-(?:flash|pro|flash-lite|flash-8b)"
    r"(?:-(?:\d{2,3}|exp|latest|\d{2}-\d{4}))?$"
)


def model_family(model_id: str) -> str:
    """Strip a leading `provider/` namespace so we rank by the bare family id."""
    return model_id.split("/", 1)[1] if "/" in model_id else model_id


def is_chat_model(provider: ProviderName, model_id: str) -> bool:
    """Return whether a listed model id is usable for chat-style generation."""
    lower = model_id.lower()
    family = model_family(lower)
    if any(marker in lower for marker in _NON_CHAT_MARKERS):
        return False
    if provider == "claude":
        return "claude" in lower
    if provider in {"openai", "oca"}:
        if re.search(r"(^|-)pro($|-)", family):
            return False
        return family.startswith(("gpt-", "o1", "o3", "o4", "o5")) or "codex" in lower
    if provider == "gemini":
        return _GEMINI_STABLE_RE.match(family) is not None
    if provider == "deepseek":
        if re.search(r"(^|[-_/])(?:v4|pro|r1)($|[-_/])", family):
            return False
        return "deepseek" in lower
    if provider == "qwen":
        if re.search(r"(^|[-_/])(?:vl|ocr)($|[-_/])", family):
            return False
        return "qwen" in lower
    if provider == "zai":
        return "glm" in family or "zai" in lower
    return True


def _model_date_score(model_id: str) -> int:
    best = 0
    for match in re.findall(r"20\d{2}(?:[-_.]?\d{2}){0,2}", model_id):
        digits = re.sub(r"\D", "", match)
        with suppress(ValueError):
            best = max(best, int(digits))
    return best


def _model_version_score(model_id: str) -> tuple[float, ...]:
    without_dates = re.sub(r"20\d{2}(?:[-_.]?\d{2}){0,2}", "", model_id)
    return tuple(float(num) for num in re.findall(r"\d+(?:\.\d+)?", without_dates))


def _model_sort_key(model: ModelInfo) -> tuple[tuple[float, ...], int, int, str]:
    family = model_family(model.id).lower()
    return (
        _model_version_score(family),
        1 if "latest" in family else 0,
        _model_date_score(family),
        model.id,
    )


def rank_chat_models(models: Iterable[ModelInfo]) -> list[ModelInfo]:
    """Filter to chat-only models and rank newest-first."""
    rows = [model for model in models if is_chat_model(model.provider, model.id)]
    return sorted(rows, key=_model_sort_key, reverse=True)


_CLOUDFLARE_HINTS = ("enable javascript and cookies to continue", "cf_chl")


def format_provider_error(provider: ProviderName, exc: Exception) -> str:
    """Return a friendly, actionable error message for known failure modes."""
    msg = str(exc)
    lower = msg.lower()
    if any(hint in lower for hint in _CLOUDFLARE_HINTS):
        return (
            f"{provider}: blocked by Cloudflare on this host (received an HTML challenge "
            "instead of an API response). Verify the base URL or run from a different network."
        )
    if "thought_signature" in lower:
        return (
            f"{provider}: the selected model needs Google's native `thought_signature` "
            "round-tripping for tool use, which the OpenAI-compatible endpoint cannot supply. "
            "Pick a stable Gemini chat model (e.g. `gemini-2.5-flash`, `gemini-2.5-pro`) or "
            "set `GEMINI_MODEL` to one of those."
        )
    if "computer use tool" in lower or "computer-use" in lower or "computer_use" in lower:
        return (
            f"{provider}: the selected model is a Computer-Use preview that requires the "
            "Computer-Use tool binding. Pick a stable chat model from the dropdown or set "
            "the provider model env var to a non-preview chat model."
        )
    if "reasoning_content" in lower:
        return (
            f"{provider}: the selected model needs provider-native `reasoning_content` "
            "round-tripping that this OpenAI-compatible adapter cannot provide. Pick a "
            "non-reasoning chat model or set the provider model env var to one."
        )
    if "invalid x-api-key" in lower:
        return f"{provider}: rejected the configured API key."
    if "authentication_error" in lower or "authenticationerror" in lower:
        return f"{provider}: authentication failed."
    return msg


def append_env_default_models(provider: ProviderName, ranked: list[ModelInfo]) -> list[ModelInfo]:
    """Append the env-configured override (if any) so users can always pick it."""
    override = explicit_provider_model(provider)
    if not override:
        return ranked
    if any(model.id == override for model in ranked):
        return ranked
    return [*ranked, ModelInfo(provider=provider, id=override, description="env override")]


def retry_max_tokens(current: int) -> int:
    """Compute the next retry max-tokens budget, clamped to shared [min, max]."""
    doubled = current * 2
    return min(RETRY_MAX_MAX_TOKENS, max(RETRY_MIN_MAX_TOKENS, doubled))


def classify_exception(
    exc: Exception,
) -> Literal["auth", "rate_limit", "bad_request", "network", "server", "unsupported"]:
    """Classify provider exceptions into normalized categories."""
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    haystack = f"{name} {message}"
    if any(hint in haystack for hint in _NOT_SUPPORTED_HINTS):
        return "unsupported"
    if "auth" in haystack or "permission" in haystack or "unauthorized" in haystack:
        return "auth"
    if "rate" in haystack or "quota" in haystack or "too many" in haystack:
        return "rate_limit"
    if "badrequest" in haystack or "invalid" in haystack or "unprocessable" in haystack:
        return "bad_request"
    if "timeout" in haystack or "connection" in haystack or "network" in haystack:
        return "network"
    return "server"


def model_info_list(
    provider: ProviderName, model_ids: Iterable[str], *, fallback: bool = False
) -> list[ModelInfo]:
    """Build normalized model list payload."""
    description = "fallback allowlist" if fallback else ""
    return [
        ModelInfo(provider=provider, id=model_id, description=description) for model_id in model_ids
    ]


def chunk_text(text: str, *, chunk_size: int = 24) -> Iterator[str]:
    """Split text into deterministic chunks for simulated streams."""
    if not text:
        return
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]


def attr(obj: object, name: str, default: object | None = None) -> object | None:
    """Safe object attribute lookup for mixed SDK response types."""
    try:
        return cast(object | None, getattr(obj, name))
    except Exception:
        return default


def mapping_value(obj: object, key: str, default: object | None = None) -> object | None:
    """Safe dict lookup without exposing `Any` in public signatures."""
    if isinstance(obj, dict):
        value = obj.get(key, default)
        return value if isinstance(value, object) else default
    return default


def normalize_usage(payload: object) -> Usage | None:
    """Normalize usage payload from SDK responses."""
    if payload is None:
        return None
    prompt_tokens = attr(payload, "prompt_tokens")
    completion_tokens = attr(payload, "completion_tokens")
    total_tokens = attr(payload, "total_tokens")
    if isinstance(payload, dict):
        prompt_tokens = payload.get("prompt_tokens")
        completion_tokens = payload.get("completion_tokens")
        total_tokens = payload.get("total_tokens")
    return Usage(
        input_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
        output_tokens=completion_tokens if isinstance(completion_tokens, int) else None,
        total_tokens=total_tokens if isinstance(total_tokens, int) else None,
    )


def text_from_content(content: object) -> str:
    """Extract text from mixed SDK content payload shapes."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            piece = text_from_content(item)
            if piece:
                parts.append(piece)
        return "".join(parts)
    if isinstance(content, dict):
        for key in ("text", "output_text", "content", "parts", "value"):
            piece = text_from_content(content.get(key))
            if piece:
                return piece
        return ""
    for name in ("text", "output_text", "content", "parts", "value"):
        nested = attr(content, name)
        if nested is None or nested is content:
            continue
        piece = text_from_content(nested)
        if piece:
            return piece
    return ""


def text_from_openai_response(response: object) -> str:
    """Extract text from OpenAI-style chat responses."""
    direct_text = text_from_content(attr(response, "text"))
    if direct_text:
        return direct_text
    if isinstance(response, dict):
        direct_text = text_from_content(response.get("text"))
        if direct_text:
            return direct_text
    choices = attr(response, "choices")
    if isinstance(response, dict):
        choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        message = attr(first, "message")
        if isinstance(first, dict):
            message = first.get("message")
        content = attr(message, "content") if message is not None else None
        if isinstance(message, dict):
            content = message.get("content")
        text = text_from_content(content)
        if text:
            return text
    return ""


def text_from_openai_stream_event(event: object) -> str:
    """Extract text chunk from one OpenAI-style stream event."""
    choices = attr(event, "choices")
    if isinstance(event, dict):
        choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    delta = attr(first, "delta")
    if isinstance(first, dict):
        delta = first.get("delta")
    if delta is None:
        return ""
    content = attr(delta, "content")
    if isinstance(delta, dict):
        content = delta.get("content")
    return text_from_content(content)


def _image_data_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _openai_compatible_user_content(
    *, prompt: str, image_attachments: tuple[ImageAttachment, ...]
) -> object:
    if not image_attachments:
        return prompt
    items: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    for image in image_attachments:
        items.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": (
                        f"data:{image.mime_type};base64,{_image_data_base64(image.data)}"
                    )
                },
            }
        )
    return items


def openai_compatible_messages_for_prompt(
    *,
    system: str | None,
    prompt: str,
    image_attachments: tuple[ImageAttachment, ...] = (),
) -> list[dict[str, object]]:
    """Build messages payload for OpenAI-compatible chat APIs."""
    messages: list[dict[str, object]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append(
        {
            "role": "user",
            "content": _openai_compatible_user_content(
                prompt=prompt, image_attachments=image_attachments
            ),
        }
    )
    return messages


def openai_compatible_messages(req: ChatRequest) -> list[dict[str, object]]:
    return openai_compatible_messages_for_prompt(
        system=req.system,
        prompt=req.prompt,
        image_attachments=tuple(req.image_attachments),
    )


def anthropic_messages(req: ChatRequest) -> list[dict[str, object]]:
    """Build messages payload for Anthropic `messages.create`."""
    if not req.image_attachments:
        return [{"role": "user", "content": req.prompt}]
    content: list[dict[str, object]] = [{"type": "text", "text": req.prompt}]
    for image in req.image_attachments:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.mime_type,
                    "data": _image_data_base64(image.data),
                },
            }
        )
    return [{"role": "user", "content": content}]


def gemini_contents(req: ChatRequest) -> object:
    """Build `contents` payload for Gemini generate_content APIs."""
    if not req.image_attachments:
        return req.prompt
    parts: list[dict[str, object]] = [{"text": req.prompt}]
    for image in req.image_attachments:
        parts.append(
            {
                "inline_data": {
                    "mime_type": image.mime_type,
                    "data": _image_data_base64(image.data),
                }
            }
        )
    return [{"role": "user", "parts": parts}]


class ProviderClientBase(BaseClient, ABC):
    """Shared adapter behavior for normalized provider clients."""

    provider: ProviderName
    default_model: str
    fallback_models: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.stream_is_simulated = False

    def list_models(self) -> list[ModelInfo]:
        try:
            raw = self._list_models_impl()
            ranked = rank_chat_models(raw)
            ranked = append_env_default_models(self.provider, ranked)
            if ranked:
                return ranked
            if self.fallback_models:
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            return []
        except LLMError:
            raise
        except Exception as exc:
            if self.fallback_models and self._is_unsupported(exc):
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            raise self._to_error(exc, model=None, action="list models") from exc

    def chat(self, req: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        try:
            response = self._chat_impl(req)
        except LLMError:
            raise
        except Exception as exc:
            raise self._to_error(exc, model=req.model, action="run prompt") from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        return ChatResponse(
            provider=req.provider,
            model=response.model,
            text=response.text,
            latency_ms=elapsed_ms,
            usage=response.usage,
            raw_id=response.raw_id,
            stream_simulated=response.stream_simulated,
        )

    def stream(self, req: ChatRequest) -> Iterable[str]:
        try:
            chunks = self._stream_impl(req)
            return chunks
        except LLMError:
            raise
        except Exception as exc:
            raise self._to_error(exc, model=req.model, action="stream prompt") from exc

    def check(self) -> CheckResult:
        started = time.perf_counter()
        try:
            return self._check_impl(started)
        except LLMError:
            raise
        except Exception as exc:
            raise self._to_error(exc, model=None, action="check credentials") from exc

    def _to_error(self, exc: Exception, *, model: str | None, action: str) -> LLMError:
        kind = classify_exception(exc)
        friendly = format_provider_error(self.provider, exc)
        message = f"Failed to {action} for provider '{self.provider}': {friendly}"
        return LLMError(provider=self.provider, model=model, kind=kind, message=message, cause=exc)

    def _is_unsupported(self, exc: Exception) -> bool:
        haystack = f"{exc.__class__.__name__} {exc}".lower()
        return any(hint in haystack for hint in _NOT_SUPPORTED_HINTS)

    def _simulate_stream(self, req: ChatRequest) -> Iterable[str]:
        logger.warning("Provider %s stream simulated for model %s", self.provider, req.model)
        self.stream_is_simulated = True
        response = self.chat(req)
        return chunk_text(response.text)

    @abstractmethod
    def _list_models_impl(self) -> list[ModelInfo]:
        """Provider-specific list-models implementation."""

    @abstractmethod
    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        """Provider-specific one-shot generation implementation."""

    @abstractmethod
    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        """Provider-specific streaming implementation."""

    @abstractmethod
    def _check_impl(self, started: float) -> CheckResult:
        """Provider-specific connection check implementation."""
