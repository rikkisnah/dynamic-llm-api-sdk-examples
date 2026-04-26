"""Tier 1: Provider client abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, ModelInfo, ProviderName


class BaseClient(ABC):
    """Abstract provider adapter contract used by services and surfaces."""

    provider: ProviderName
    default_model: str
    stream_is_simulated: bool

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """List available models for this provider."""

    @abstractmethod
    def chat(self, req: ChatRequest) -> ChatResponse:
        """Run a non-streaming generation request."""

    @abstractmethod
    def stream(self, req: ChatRequest) -> Iterable[str]:
        """Yield text chunks for streaming responses."""

    @abstractmethod
    def check(self) -> CheckResult:
        """Validate credential + endpoint health with a minimal call."""
