"""Tier 2: DeepSeek adapter using OpenAI-compatible SDK path."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import cast

from llm_examples.config import get_provider_config
from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, ModelInfo, ProviderName
from llm_examples.providers._common import (
    ProviderClientBase,
    attr,
    model_info_list,
    normalize_usage,
    text_from_openai_response,
)

DEFAULT_MODEL = "deepseek-chat"
FALLBACK_MODELS = ("deepseek-chat", "deepseek-reasoner")


class DeepSeekProvider(ProviderClientBase):
    """DeepSeek client through the OpenAI-compatible endpoint."""

    provider: ProviderName = "deepseek"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)
        self._client: object | None = None

    def _sdk_client(self) -> object:
        if self._client is None:
            from openai import OpenAI  # type: ignore[import-not-found]

            kwargs: dict[str, object] = {"api_key": self._config.api_key}
            kwargs["base_url"] = self._config.base_url or "https://api.deepseek.com"
            self._client = OpenAI(**kwargs)
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
        chat_obj = attr(self._sdk_client(), "chat")
        completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
        create_fn = attr(completions_obj, "create")
        if not callable(create_fn):
            raise RuntimeError("DeepSeek OpenAI-compatible chat API unavailable.")

        messages: list[dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        response = create_fn(model=req.model, messages=messages, max_tokens=req.max_tokens, stream=False)
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=text_from_openai_response(response),
            latency_ms=0.0,
            usage=normalize_usage(attr(response, "usage")),
            raw_id=cast(str | None, attr(response, "id")),
            stream_simulated=False,
        )

    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        chat_obj = attr(self._sdk_client(), "chat")
        completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
        create_fn = attr(completions_obj, "create")
        if not callable(create_fn):
            return self._simulate_stream(req)

        messages: list[dict[str, str]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        self.stream_is_simulated = False
        stream_obj = create_fn(model=req.model, messages=messages, max_tokens=req.max_tokens, stream=True)
        chunks: list[str] = []
        for event in stream_obj:
            choices = attr(event, "choices")
            if not isinstance(choices, list) or not choices:
                continue
            delta = attr(choices[0], "delta")
            piece = attr(delta, "content") if delta is not None else None
            if isinstance(piece, str) and piece:
                chunks.append(piece)
        return chunks

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
