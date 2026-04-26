"""Shared test helpers and fakes."""

from __future__ import annotations

from collections.abc import Iterable

from llm_examples.domain_types import (
    ChatRequest,
    ChatResponse,
    CheckResult,
    ModelInfo,
    ProviderName,
    Usage,
)
from llm_examples.llm_client import BaseClient


class FakeClient(BaseClient):
    """Deterministic fake implementation for service-layer tests."""

    def __init__(self, provider: ProviderName = "openai", model: str = "fake-model") -> None:
        self.provider = provider
        self.default_model = model
        self.stream_is_simulated = False

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(provider=self.provider, id=self.default_model, description="fake")]

    def chat(self, req: ChatRequest) -> ChatResponse:
        return ChatResponse(
            provider=req.provider,
            model=req.model,
            text=f"echo:{req.prompt}",
            latency_ms=1.0,
            usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            raw_id="fake-id",
        )

    def stream(self, req: ChatRequest) -> Iterable[str]:
        self.stream_is_simulated = True
        return ["echo:", req.prompt]

    def check(self) -> CheckResult:
        return CheckResult(provider=self.provider, ok=True, latency_ms=1.0, detail="ok")
