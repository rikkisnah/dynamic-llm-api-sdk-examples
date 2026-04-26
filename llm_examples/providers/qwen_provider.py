"""Tier 2: Qwen DashScope native SDK adapter."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import cast

from llm_examples.config import get_provider_config
from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, ModelInfo, ProviderName
from llm_examples.providers._common import (
    ProviderClientBase,
    attr,
    mapping_value,
    model_info_list,
    normalize_usage,
)

DEFAULT_MODEL = "qwen-plus"
FALLBACK_MODELS = ("qwen-plus", "qwen-turbo")


def _extract_qwen_text(response: object) -> str:
    output = attr(response, "output", response)
    choices = attr(output, "choices", mapping_value(output, "choices"))
    if isinstance(choices, list) and choices:
        first = choices[0]
        message = attr(first, "message", mapping_value(first, "message"))
        content = attr(message, "content", mapping_value(message, "content"))
        if isinstance(content, str):
            return content
    return ""


class QwenProvider(ProviderClientBase):
    """Qwen provider client using DashScope SDK."""

    provider: ProviderName = "qwen"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)

    def _generation_class(self) -> object:
        from dashscope import Generation  # type: ignore[import-not-found]

        return Generation

    def _list_models_impl(self) -> list[ModelInfo]:
        return model_info_list(self.provider, self.fallback_models, fallback=True)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        generation = self._generation_class()
        call_fn = attr(generation, "call")
        if not callable(call_fn):
            raise RuntimeError("DashScope Generation.call is unavailable.")
        kwargs: dict[str, object] = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "api_key": self._config.api_key,
            "result_format": "message",
            "max_tokens": req.max_tokens,
        }
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        if req.system:
            kwargs["system"] = req.system
        response = call_fn(**kwargs)
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=_extract_qwen_text(response),
            latency_ms=0.0,
            usage=normalize_usage(attr(response, "usage", mapping_value(response, "usage"))),
            raw_id=cast(str | None, attr(response, "request_id", mapping_value(response, "request_id"))),
            stream_simulated=False,
        )

    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        generation = self._generation_class()
        call_fn = attr(generation, "call")
        if not callable(call_fn):
            return self._simulate_stream(req)
        kwargs: dict[str, object] = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "api_key": self._config.api_key,
            "result_format": "message",
            "max_tokens": req.max_tokens,
            "stream": True,
            "incremental_output": True,
        }
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        if req.system:
            kwargs["system"] = req.system
        self.stream_is_simulated = False
        stream = call_fn(**kwargs)
        pieces: list[str] = []
        for item in stream:
            text = _extract_qwen_text(item)
            if text:
                pieces.append(text)
        if not pieces:
            return self._simulate_stream(req)
        return pieces

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._chat_impl(
            ChatRequest(
                provider=self.provider,
                model=self.default_model,
                prompt="ping",
                max_tokens=1,
            )
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
