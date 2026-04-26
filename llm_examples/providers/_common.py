"""Tier 2: Shared provider adapter helpers."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Literal

from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, LLMError, ModelInfo, Usage
from llm_examples.llm_client import BaseClient

logger = logging.getLogger(__name__)

_NOT_SUPPORTED_HINTS = ("not support", "unsupported", "not implemented", "does not support")


def classify_exception(exc: Exception) -> Literal[
    "auth", "rate_limit", "bad_request", "network", "server", "unsupported"
]:
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


def model_info_list(provider: str, model_ids: Iterable[str], *, fallback: bool = False) -> list[ModelInfo]:
    """Build normalized model list payload."""
    description = "fallback allowlist" if fallback else ""
    return [ModelInfo(provider=provider, id=model_id, description=description) for model_id in model_ids]


def chunk_text(text: str, *, chunk_size: int = 24) -> Iterator[str]:
    """Split text into deterministic chunks for simulated streams."""
    if not text:
        return
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]


def attr(obj: object, name: str, default: object | None = None) -> object | None:
    """Safe object attribute lookup for mixed SDK response types."""
    try:
        return getattr(obj, name)
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


def text_from_openai_response(response: object) -> str:
    """Extract text from OpenAI-style chat responses."""
    choices = attr(response, "choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        message = attr(first, "message")
        content = attr(message, "content") if message is not None else None
        if isinstance(content, str):
            return content
    return ""


class ProviderClientBase(BaseClient, ABC):
    """Shared adapter behavior for normalized provider clients."""

    provider: str
    default_model: str
    fallback_models: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.stream_is_simulated = False

    def list_models(self) -> list[ModelInfo]:
        try:
            models = self._list_models_impl()
            if models:
                return models
            if self.fallback_models:
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            return []
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
            if self.fallback_models and self._is_unsupported(exc):
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            raise self._to_error(exc, model=None, action="list models")

    def chat(self, req: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        try:
            response = self._chat_impl(req)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
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
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._to_error(exc, model=req.model, action="stream prompt") from exc

    def check(self) -> CheckResult:
        started = time.perf_counter()
        try:
            return self._check_impl(started)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._to_error(exc, model=None, action="check credentials") from exc

    def _to_error(self, exc: Exception, *, model: str | None, action: str) -> LLMError:
        kind = classify_exception(exc)
        message = f"Failed to {action} for provider '{self.provider}': {exc}"
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
