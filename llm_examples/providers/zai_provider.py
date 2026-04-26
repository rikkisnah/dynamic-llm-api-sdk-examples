"""Tier 2: Z.ai SDK adapter with httpx fallback path."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import cast

import httpx

from llm_examples.config import get_provider_config
from llm_examples.domain_types import (
    ChatRequest,
    ChatResponse,
    CheckResult,
    ModelInfo,
    ProviderName,
    Usage,
)
from llm_examples.providers._common import (
    ProviderClientBase,
    attr,
    model_info_list,
    normalize_usage,
    text_from_content,
    text_from_openai_response,
    text_from_openai_stream_event,
)

DEFAULT_MODEL = "glm-4.6"
FALLBACK_MODELS = ("glm-4.6", "glm-4.5-air")
RETRY_MIN_MAX_TOKENS = 512
RETRY_MAX_MAX_TOKENS = 2048


def _is_token_limit_finish(finish_reason: object) -> bool:
    value = finish_reason if isinstance(finish_reason, str) else str(finish_reason)
    normalized = value.strip().lower()
    return normalized in {"length", "max_tokens", "finishreason.max_tokens"}


def _raise_if_empty_due_token_limit(
    *, text: str, finish_reason: object, max_tokens: int, model: str
) -> None:
    if _is_empty_due_token_limit(text=text, finish_reason=finish_reason):
        raise RuntimeError(
            f"Z.ai returned empty assistant content due token limit for model '{model}' "
            f"(max_tokens={max_tokens}). Increase max_tokens."
        )


def _is_empty_due_token_limit(*, text: str, finish_reason: object) -> bool:
    if text.strip():
        return False
    return _is_token_limit_finish(finish_reason)


def _retry_max_tokens(max_tokens: int) -> int:
    doubled = max_tokens * 2
    return min(RETRY_MAX_MAX_TOKENS, max(RETRY_MIN_MAX_TOKENS, doubled))


def _extract_sdk_chat_fields(response: object) -> tuple[str, object, Usage | None, str | None]:
    choices = attr(response, "choices")
    first_choice = choices[0] if isinstance(choices, list) and choices else None
    finish_reason = attr(first_choice, "finish_reason") if first_choice is not None else None
    text = text_from_openai_response(response)
    usage = normalize_usage(attr(response, "usage"))
    raw_id = cast(str | None, attr(response, "id"))
    return text, finish_reason, usage, raw_id


def _extract_http_chat_fields(data: object) -> tuple[str, object, Usage | None, str | None]:
    if not isinstance(data, dict):
        return "", None, None, None

    text = ""
    finish_reason: object = None
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        finish_reason = choices[0].get("finish_reason")
        message = choices[0].get("message")
        if isinstance(message, dict):
            text = text_from_content(message.get("content"))
    usage_payload = data.get("usage")
    usage = normalize_usage(usage_payload if isinstance(usage_payload, dict) else None)
    raw_id = data.get("id")
    return text, finish_reason, usage, raw_id if isinstance(raw_id, str) else None


class ZAIProvider(ProviderClientBase):
    """Z.ai provider using `zai-sdk` when available, else OpenAI-compatible HTTP."""

    provider: ProviderName = "zai"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)
        self._client: object | None = None

    def _sdk_client(self) -> object | None:
        if self._client is not None:
            return self._client
        try:
            from zai import ZaiClient
        except Exception:
            return None
        if self._config.base_url:
            self._client = ZaiClient(api_key=self._config.api_key, base_url=self._config.base_url)
        else:
            self._client = ZaiClient(api_key=self._config.api_key)
        return self._client

    def _http_client(self) -> httpx.Client:
        base_url = self._config.base_url or "https://api.z.ai/api/paas/v4"
        headers = {"Authorization": f"Bearer {self._config.api_key}"}
        return httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30.0)

    def _list_models_impl(self) -> list[ModelInfo]:
        client = self._sdk_client()
        if client is not None:
            models_obj = attr(client, "models")
            list_fn = attr(models_obj, "list") if models_obj is not None else None
            if callable(list_fn):
                payload = list_fn()
                data = attr(payload, "data", payload)
                model_ids: list[str] = []
                if isinstance(data, list):
                    for item in data:
                        model_id = attr(item, "id")
                        if isinstance(model_id, str):
                            model_ids.append(model_id)
                if model_ids:
                    return model_info_list(self.provider, model_ids)

        with self._http_client() as http:
            response = http.get("/models")
            if response.status_code >= 400:
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            payload = response.json()
            data = payload.get("data")
            fallback_model_ids: list[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        model_id = item.get("id")
                        if isinstance(model_id, str):
                            fallback_model_ids.append(model_id)
            if not fallback_model_ids:
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            return model_info_list(self.provider, fallback_model_ids)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        client = self._sdk_client()
        if client is not None:
            chat_obj = attr(client, "chat")
            completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
            create_fn = attr(completions_obj, "create")
            if callable(create_fn):
                sdk_messages: list[dict[str, str]] = []
                if req.system:
                    sdk_messages.append({"role": "system", "content": req.system})
                sdk_messages.append({"role": "user", "content": req.prompt})
                response = create_fn(
                    model=req.model,
                    messages=sdk_messages,
                    max_tokens=req.max_tokens,
                    stream=False,
                )
                text, finish_reason, usage, raw_id = _extract_sdk_chat_fields(response)
                tokens_used = req.max_tokens
                if _is_empty_due_token_limit(text=text, finish_reason=finish_reason):
                    retry_tokens = _retry_max_tokens(req.max_tokens)
                    if retry_tokens > req.max_tokens:
                        retry_response = create_fn(
                            model=req.model,
                            messages=sdk_messages,
                            max_tokens=retry_tokens,
                            stream=False,
                        )
                        text, finish_reason, usage, raw_id = _extract_sdk_chat_fields(
                            retry_response
                        )
                        tokens_used = retry_tokens
                _raise_if_empty_due_token_limit(
                    text=text,
                    finish_reason=finish_reason,
                    max_tokens=tokens_used,
                    model=req.model,
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

        with self._http_client() as http:
            http_messages: list[dict[str, str]] = [{"role": "user", "content": req.prompt}]
            if req.system:
                http_messages.insert(0, {"role": "system", "content": req.system})
            def http_chat(max_tokens: int) -> tuple[str, object, Usage | None, str | None]:
                payload = {
                    "model": req.model,
                    "messages": http_messages,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                response = http.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return _extract_http_chat_fields(data)

            text, finish_reason, usage, raw_id = http_chat(req.max_tokens)
            tokens_used = req.max_tokens
            if _is_empty_due_token_limit(text=text, finish_reason=finish_reason):
                retry_tokens = _retry_max_tokens(req.max_tokens)
                if retry_tokens > req.max_tokens:
                    text, finish_reason, usage, raw_id = http_chat(retry_tokens)
                    tokens_used = retry_tokens
            _raise_if_empty_due_token_limit(
                text=text,
                finish_reason=finish_reason,
                max_tokens=tokens_used,
                model=req.model,
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
        client = self._sdk_client()
        if client is None:
            return self._simulate_stream(req)

        chat_obj = attr(client, "chat")
        completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
        create_fn = attr(completions_obj, "create")
        if not callable(create_fn):
            return self._simulate_stream(req)

        messages: list[dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})
        self.stream_is_simulated = False
        stream = create_fn(
            model=req.model, messages=messages, max_tokens=req.max_tokens, stream=True
        )
        chunks: list[str] = []
        for event in stream:
            piece = text_from_openai_stream_event(event)
            if piece:
                chunks.append(piece)
        if not chunks:
            return self._simulate_stream(req)
        return chunks

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
