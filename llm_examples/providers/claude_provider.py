"""Tier 2: Anthropic Claude native SDK adapter."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import cast

from llm_examples.config import get_provider_config
from llm_examples.domain_types import (
    ChatRequest,
    ChatResponse,
    CheckResult,
    ModelInfo,
    ProviderName,
)
from llm_examples.providers._common import (
    ProviderClientBase,
    anthropic_messages,
    attr,
    model_info_list,
    normalize_usage,
)

DEFAULT_MODEL = "claude-haiku-4-5"
FALLBACK_MODELS = ("claude-haiku-4-5", "claude-sonnet-4-5")


def _extract_claude_text(response: object) -> str:
    content = attr(response, "content")
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for block in content:
        block_type = attr(block, "type")
        if block_type == "text":
            text = attr(block, "text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


class ClaudeProvider(ProviderClientBase):
    """Anthropic provider client using `anthropic` SDK."""

    provider: ProviderName = "claude"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)
        self._client: object | None = None

    def _sdk_client(self) -> object:
        if self._client is None:
            from anthropic import Anthropic

            if self._config.base_url:
                self._client = Anthropic(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                )
            else:
                self._client = Anthropic(api_key=self._config.api_key)
        return self._client

    def _list_models_impl(self) -> list[ModelInfo]:
        models_obj = attr(self._sdk_client(), "models")
        list_fn = attr(models_obj, "list") if models_obj is not None else None
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
        if not model_ids:
            return model_info_list(self.provider, self.fallback_models, fallback=True)
        return model_info_list(self.provider, model_ids)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        messages_obj = attr(self._sdk_client(), "messages")
        create_fn = attr(messages_obj, "create")
        if not callable(create_fn):
            raise RuntimeError("Anthropic SDK messages.create is unavailable.")
        kwargs: dict[str, object] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": anthropic_messages(req),
        }
        if req.system:
            kwargs["system"] = req.system
        response = create_fn(**kwargs)
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=_extract_claude_text(response),
            latency_ms=0.0,
            usage=normalize_usage(attr(response, "usage")),
            raw_id=cast(str | None, attr(response, "id")),
            stream_simulated=False,
        )

    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        messages_obj = attr(self._sdk_client(), "messages")
        stream_fn = attr(messages_obj, "stream")
        if not callable(stream_fn):
            return self._simulate_stream(req)

        kwargs: dict[str, object] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": anthropic_messages(req),
        }
        if req.system:
            kwargs["system"] = req.system

        self.stream_is_simulated = False
        stream_ctx = stream_fn(**kwargs)
        chunks: list[str] = []
        with stream_ctx as stream:
            text_stream = attr(stream, "text_stream")
            if isinstance(text_stream, Iterable) and not isinstance(text_stream, (str, bytes)):
                for piece in text_stream:
                    if isinstance(piece, str) and piece:
                        chunks.append(piece)
        if not chunks:
            return self._simulate_stream(req)
        return chunks

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
