"""Tier 2: Google Gemini native SDK adapter (`google-genai`)."""

from __future__ import annotations

import time
from collections.abc import Iterable

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
    attr,
    gemini_contents,
    model_info_list,
    normalize_usage,
    text_from_content,
)

DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-2.5-pro")


def _extract_gemini_text(response: object) -> str:
    text = attr(response, "text")
    if isinstance(text, str) and text:
        return text

    candidates = attr(response, "candidates")
    if not isinstance(candidates, list):
        return text if isinstance(text, str) else ""

    chunks: list[str] = []
    for candidate in candidates:
        content = attr(candidate, "content")
        if content is None:
            continue
        piece = text_from_content(content)
        if piece:
            chunks.append(piece)
    if chunks:
        return "".join(chunks)
    return text if isinstance(text, str) else ""


class GeminiProvider(ProviderClientBase):
    """Gemini provider client using the `google-genai` SDK."""

    provider: ProviderName = "gemini"
    default_model = DEFAULT_MODEL
    fallback_models = FALLBACK_MODELS

    def __init__(self) -> None:
        super().__init__()
        self._config = get_provider_config(self.provider)
        self._client: object | None = None

    def _sdk_client(self) -> object:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._config.api_key)
        return self._client

    def _list_models_impl(self) -> list[ModelInfo]:
        models_obj = attr(self._sdk_client(), "models")
        list_fn = attr(models_obj, "list") if models_obj is not None else None
        if not callable(list_fn):
            return model_info_list(self.provider, self.fallback_models, fallback=True)
        payload = list_fn()
        model_ids: list[str] = []
        for item in payload:
            model_name = attr(item, "name")
            if isinstance(model_name, str):
                model_ids.append(model_name)
        if not model_ids:
            return model_info_list(self.provider, self.fallback_models, fallback=True)
        return model_info_list(self.provider, model_ids)

    def _chat_impl(self, req: ChatRequest) -> ChatResponse:
        models_obj = attr(self._sdk_client(), "models")
        generate_fn = attr(models_obj, "generate_content") if models_obj is not None else None
        if not callable(generate_fn):
            raise RuntimeError("google-genai models.generate_content is unavailable.")

        config: dict[str, object] = {"max_output_tokens": req.max_tokens}
        if req.system:
            config["system_instruction"] = req.system
        response = generate_fn(model=req.model, contents=gemini_contents(req), config=config)
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=_extract_gemini_text(response),
            latency_ms=0.0,
            usage=normalize_usage(attr(response, "usage_metadata")),
            raw_id=None,
            stream_simulated=False,
        )

    def _stream_impl(self, req: ChatRequest) -> Iterable[str]:
        models_obj = attr(self._sdk_client(), "models")
        generate_stream_fn = (
            attr(models_obj, "generate_content_stream") if models_obj is not None else None
        )
        if not callable(generate_stream_fn):
            return self._simulate_stream(req)

        config: dict[str, object] = {"max_output_tokens": req.max_tokens}
        if req.system:
            config["system_instruction"] = req.system

        self.stream_is_simulated = False
        pieces: list[str] = []
        stream = generate_stream_fn(model=req.model, contents=gemini_contents(req), config=config)
        for item in stream:
            piece = _extract_gemini_text(item)
            if piece:
                pieces.append(piece)
        if not pieces:
            return self._simulate_stream(req)
        return pieces

    def _check_impl(self, started: float) -> CheckResult:
        _ = self._list_models_impl()
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckResult(provider=self.provider, ok=True, latency_ms=latency_ms, detail="ok")
