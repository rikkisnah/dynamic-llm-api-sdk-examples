"""Tier 3: Provider registry and client dispatch."""

from __future__ import annotations

from collections.abc import Mapping

from llm_examples.domain_types import ProviderName
from llm_examples.llm_client import BaseClient
from llm_examples.providers import (
    ClaudeProvider,
    DeepSeekProvider,
    GeminiProvider,
    OCAProvider,
    OpenAIProvider,
    QwenProvider,
    ZAIProvider,
)

PROVIDERS: tuple[ProviderName, ...] = (
    "openai",
    "claude",
    "gemini",
    "deepseek",
    "qwen",
    "zai",
    "oca",
)

_CLIENTS: Mapping[ProviderName, type[BaseClient]] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "zai": ZAIProvider,
    "oca": OCAProvider,
}


def get_client(provider: ProviderName) -> BaseClient:
    """Build a provider adapter by name."""
    client_cls = _CLIENTS[provider]
    return client_cls()
