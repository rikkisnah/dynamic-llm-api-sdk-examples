"""Tier 0: Core domain types and normalized error model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

ProviderName = Literal["openai", "claude", "gemini", "deepseek", "qwen", "zai"]
ErrorKind = Literal["auth", "rate_limit", "bad_request", "network", "server", "unsupported"]


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Provider model metadata."""

    provider: ProviderName
    id: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Usage:
    """Token usage metadata normalized across providers."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """Normalized request for a text generation call."""

    provider: ProviderName
    model: str
    prompt: str
    system: str | None = None
    max_tokens: int = 512
    stream: bool = False


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Normalized chat completion response."""

    provider: ProviderName
    model: str
    text: str
    latency_ms: float
    usage: Usage | None = None
    raw_id: str | None = None
    stream_simulated: bool = False


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Credential and endpoint check result."""

    provider: ProviderName
    ok: bool
    latency_ms: float
    detail: str


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Resolved provider configuration from environment."""

    provider: ProviderName
    api_key: str
    base_url: str | None = None


class LLMError(Exception):
    """Normalized exception type raised by all layers."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        model: str | None,
        kind: ErrorKind,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.kind = kind
        self.message = message
        self.cause = cause
        super().__init__(message)

    def to_dict(self) -> Mapping[str, object]:
        """Serialize a safe error payload for CLI/UI output."""
        return {
            "provider": self.provider,
            "model": self.model,
            "kind": self.kind,
            "message": self.message,
        }


class MissingCredential(LLMError):
    """Credential-specific auth error."""

    def __init__(self, *, provider: ProviderName, env_var: str) -> None:
        message = f"Missing credential for provider '{provider}'. Expected environment variable: {env_var}."
        super().__init__(provider=provider, model=None, kind="auth", message=message, cause=None)
