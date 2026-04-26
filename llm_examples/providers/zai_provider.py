"""Tier 2: Z.ai SDK adapter with httpx fallback path."""

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

DEFAULT_MODEL = "glm-4.6"
FALLBACK_MODELS = ("glm-4.6", "glm-4.5-air")


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
            from zai import Client as ZAIClient  # type: ignore[import-not-found]
        except Exception:
            return None
        kwargs: dict[str, object] = {"api_key": self._config.api_key}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        self._client = ZAIClient(**kwargs)
        return self._client

    def _http_client(self) -> object:
        import httpx

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
            model_ids: list[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        model_id = item.get("id")
                        if isinstance(model_id, str):
                            model_ids.append(model_id)
            if not model_ids:
                return model_info_list(self.provider, self.fallback_models, fallback=True)
            return model_info_list(self.provider, model_ids)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        client = self._sdk_client()
        if client is not None:
            chat_obj = attr(client, "chat")
            completions_obj = attr(chat_obj, "completions") if chat_obj is not None else None
            create_fn = attr(completions_obj, "create")
            if callable(create_fn):
                messages: list[dict[str, str]] = []
                if req.system:
                    messages.append({"role": "system", "content": req.system})
                messages.append({"role": "user", "content": req.prompt})
                response = create_fn(
                    model=req.model,
                    messages=messages,
                    max_tokens=req.max_tokens,
                    stream=False,
                )
                return ChatResponse(
                    provider=req.provider,
                    model=req.model,
                    text=text_from_openai_response(response),
                    latency_ms=0.0,
                    usage=normalize_usage(attr(response, "usage")),
                    raw_id=cast(str | None, attr(response, "id")),
                    stream_simulated=False,
                )

        with self._http_client() as http:
            payload = {
                "model": req.model,
                "messages": [{"role": "user", "content": req.prompt}],
                "max_tokens": req.max_tokens,
                "stream": False,
            }
            if req.system:
                payload["messages"].insert(0, {"role": "system", "content": req.system})
            response = http.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices")
            text = ""
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                message = choices[0].get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        text = content
            usage_payload = data.get("usage")
            usage = normalize_usage(usage_payload if isinstance(usage_payload, dict) else None)
            raw_id = data.get("id")
            return ChatResponse(
                provider=req.provider,
                model=req.model,
                text=text,
                latency_ms=0.0,
                usage=usage,
                raw_id=raw_id if isinstance(raw_id, str) else None,
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
        stream = create_fn(model=req.model, messages=messages, max_tokens=req.max_tokens, stream=True)
        chunks: list[str] = []
        for event in stream:
            choices = attr(event, "choices")
            if not isinstance(choices, list) or not choices:
                continue
            delta = attr(choices[0], "delta")
            piece = attr(delta, "content")
            if isinstance(piece, str) and piece:
                chunks.append(piece)
        if not chunks:
            return self._simulate_stream(req)
        return chunks

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
