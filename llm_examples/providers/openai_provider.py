"""Tier 2: OpenAI native SDK adapter."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import cast

from llm_examples.config import get_provider_config
from llm_examples.domain_types import (
    ChatRequest,
    ChatResponse,
    CheckResult,
    LLMError,
    ModelInfo,
    ProviderName,
    Usage,
)
from llm_examples.providers._common import (
    ProviderClientBase,
    attr,
    model_info_list,
    normalize_usage,
    openai_compatible_messages,
    text_from_openai_response,
    text_from_openai_stream_event,
)

DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_MODELS = ("gpt-4o-mini", "gpt-4.1-mini")
RETRY_MIN_MAX_TOKENS = 2048
RETRY_MAX_MAX_TOKENS = 4096


def _uses_max_completion_tokens(exc: Exception) -> bool:
    message = str(exc).lower()
    return "max_tokens" in message and "max_completion_tokens" in message


def _openai_is_token_limit_finish(finish_reason: object) -> bool:
    value = finish_reason if isinstance(finish_reason, str) else str(finish_reason)
    normalized = value.strip().lower()
    return normalized in {"length", "max_tokens", "finishreason.max_tokens"}


def _openai_retry_max_tokens(max_tokens: int) -> int:
    doubled = max_tokens * 2
    return min(RETRY_MAX_MAX_TOKENS, max(RETRY_MIN_MAX_TOKENS, doubled))


def _openai_extract_chat_fields(response: object) -> tuple[str, object, Usage | None, str | None]:
    choices = attr(response, "choices")
    first_choice = choices[0] if isinstance(choices, list) and choices else None
    finish_reason = attr(first_choice, "finish_reason") if first_choice is not None else None
    text = text_from_openai_response(response)
    usage = normalize_usage(attr(response, "usage"))
    raw_id = cast(str | None, attr(response, "id"))
    return text, finish_reason, usage, raw_id


def _openai_is_empty_due_token_limit(*, text: str, finish_reason: object) -> bool:
    if text.strip():
        return False
    return _openai_is_token_limit_finish(finish_reason)


def _openai_raise_if_empty_due_token_limit(
    *,
    provider: ProviderName,
    model: str,
    text: str,
    finish_reason: object,
    max_tokens: int,
) -> None:
    if _openai_is_empty_due_token_limit(text=text, finish_reason=finish_reason):
        raise LLMError(
            provider=provider,
            model=model,
            kind="bad_request",
            message=(
                f"OpenAI returned empty assistant content due token limit for model '{model}' "
                f"(max_tokens={max_tokens}). Increase max_tokens."
            ),
        )


class OpenAIProvider(ProviderClientBase):
    """OpenAI provider client using the official `openai` SDK."""

    provider: ProviderName = "openai"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)
        self._client: object | None = None

    def _sdk_client(self) -> object:
        if self._client is None:
            from openai import OpenAI

            if self._config.base_url:
                self._client = OpenAI(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                )
            else:
                self._client = OpenAI(api_key=self._config.api_key)
        return self._client

    def _list_models_impl(self) -> list[ModelInfo]:
        models_obj = attr(self._sdk_client(), "models")
        if models_obj is None:
            return model_info_list(self.provider, self.fallback_models, fallback=True)
        list_fn = attr(models_obj, "list")
        if not callable(list_fn):
            return model_info_list(self.provider, self.fallback_models, fallback=True)
        payload = list_fn()
        data = attr(payload, "data", payload)
        model_ids: list[str] = []
        if isinstance(data, list):
            for item in data:
                model_id = attr(item, "id")
                if isinstance(model_id, str):
                    model_ids.append(model_id)
        return model_info_list(self.provider, model_ids)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        chat_obj = attr(self._sdk_client(), "chat")
        completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
        create_fn = attr(completions_obj, "create")
        if not callable(create_fn):
            raise RuntimeError("OpenAI SDK chat.completions.create is unavailable.")

        messages = openai_compatible_messages(req)

        def _create_chat(max_tokens: int) -> object:
            try:
                return create_fn(
                    model=req.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=False,
                )
            except Exception as exc:
                if not _uses_max_completion_tokens(exc):
                    raise
                return create_fn(
                    model=req.model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    stream=False,
                )

        response = _create_chat(req.max_tokens)
        text, finish_reason, usage, raw_id = _openai_extract_chat_fields(response)
        tokens_used = req.max_tokens
        if _openai_is_empty_due_token_limit(text=text, finish_reason=finish_reason):
            retry_tokens = _openai_retry_max_tokens(req.max_tokens)
            if retry_tokens > req.max_tokens:
                response = _create_chat(retry_tokens)
                text, finish_reason, usage, raw_id = _openai_extract_chat_fields(response)
                tokens_used = retry_tokens
        _openai_raise_if_empty_due_token_limit(
            provider=req.provider,
            model=req.model,
            text=text,
            finish_reason=finish_reason,
            max_tokens=tokens_used,
        )
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=text,
            latency_ms=0.0,
            usage=usage,
            raw_id=raw_id,
            stream_simulated=False,
        )

    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        chat_obj = attr(self._sdk_client(), "chat")
        completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
        create_fn = attr(completions_obj, "create")
        if not callable(create_fn):
            return self._simulate_stream(req)

        messages = openai_compatible_messages(req)

        self.stream_is_simulated = False
        try:
            stream_obj = create_fn(
                model=req.model, messages=messages, max_tokens=req.max_tokens, stream=True
            )
        except Exception as exc:
            if not _uses_max_completion_tokens(exc):
                raise
            stream_obj = create_fn(
                model=req.model,
                messages=messages,
                max_completion_tokens=req.max_tokens,
                stream=True,
            )
        chunks: list[str] = []
        for event in stream_obj:
            piece = text_from_openai_stream_event(event)
            if piece:
                chunks.append(piece)
        return chunks

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
