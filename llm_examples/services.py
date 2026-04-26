"""Tier 4: Surface-agnostic service layer for CLI and UI."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass

from llm_examples.domain_types import ChatRequest, ChatResponse, CheckResult, LLMError, ModelInfo, ProviderName
from llm_examples.registry import get_client


@dataclass(frozen=True, slots=True)
class StreamResult:
    """Structured stream response for parity-friendly CLI/UI rendering."""

    provider: ProviderName
    model: str
    chunks: Iterable[str]
    simulated: bool


def list_models(provider: ProviderName) -> list[ModelInfo]:
    """List models using provider adapter normalization."""
    client = get_client(provider)
    return client.list_models()


def run_prompt(
    *,
    provider: ProviderName,
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 512,
) -> ChatResponse:
    """Run one-shot prompt and normalize response metadata."""
    client = get_client(provider)
    effective_model = model or client.default_model
    request = ChatRequest(
        provider=provider,
        model=effective_model,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
        stream=False,
    )
    started = time.perf_counter()
    try:
        response = client.chat(request)
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalized below
        raise LLMError(
            provider=provider,
            model=effective_model,
            kind="server",
            message=f"Unexpected service error: {exc}",
            cause=exc,
        ) from exc
    service_latency = (time.perf_counter() - started) * 1000
    return ChatResponse(
        provider=response.provider,
        model=response.model,
        text=response.text,
        latency_ms=response.latency_ms or service_latency,
        usage=response.usage,
        raw_id=response.raw_id,
        stream_simulated=response.stream_simulated,
    )


def stream_prompt(
    *,
    provider: ProviderName,
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 512,
) -> StreamResult:
    """Run streaming prompt and expose whether stream is simulated."""
    client = get_client(provider)
    effective_model = model or client.default_model
    request = ChatRequest(
        provider=provider,
        model=effective_model,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
        stream=True,
    )
    try:
        chunks = client.stream(request)
        return StreamResult(
            provider=provider,
            model=effective_model,
            chunks=chunks,
            simulated=client.stream_is_simulated,
        )
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalized below
        raise LLMError(
            provider=provider,
            model=effective_model,
            kind="server",
            message=f"Unexpected service error: {exc}",
            cause=exc,
        ) from exc


def check_connection(provider: ProviderName) -> CheckResult:
    """Validate provider key and endpoint."""
    client = get_client(provider)
    return client.check()
