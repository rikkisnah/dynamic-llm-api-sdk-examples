"""Tier 5: CLI helpers for provider resolution from env defaults."""

from __future__ import annotations

from typing import cast

from llm_examples.config import resolve_default_provider
from llm_examples.domain_types import ProviderName
from llm_examples.registry import PROVIDERS

DEFAULT_PROVIDER_FALLBACK: ProviderName = "openai"


def resolve_provider(value: str | None) -> ProviderName:
    """Return the explicit `--provider` value or the env-driven default."""
    if isinstance(value, str) and value:
        return cast(ProviderName, value)
    return resolve_default_provider(options=PROVIDERS, fallback=DEFAULT_PROVIDER_FALLBACK)
