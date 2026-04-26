"""Tier 0: Environment-driven provider configuration loading."""

from __future__ import annotations

import os
from typing import Mapping

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs
    def load_dotenv() -> bool:
        return False

from llm_examples.domain_types import MissingCredential, ProviderConfig, ProviderName

load_dotenv()

_ENV_KEYS: Mapping[ProviderName, tuple[str, str | None]] = {
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "claude": ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
    "gemini": ("GEMINI_API_KEY", None),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "qwen": ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL"),
    "zai": ("ZAI_API_KEY", "ZAI_BASE_URL"),
}

_DEFAULT_BASE_URLS: Mapping[ProviderName, str] = {
    "deepseek": "https://api.deepseek.com",
    "zai": "https://api.z.ai/api/paas/v4",
}


def provider_env_names(provider: ProviderName) -> tuple[str, str | None]:
    """Return (api_key_env, base_url_env) for a provider."""
    return _ENV_KEYS[provider]


def get_provider_config(provider: ProviderName) -> ProviderConfig:
    """Resolve provider configuration from current process environment."""
    api_key_env, base_url_env = provider_env_names(provider)
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        raise MissingCredential(provider=provider, env_var=api_key_env)

    base_url: str | None = None
    if base_url_env is not None:
        configured = os.getenv(base_url_env, "").strip()
        base_url = configured or _DEFAULT_BASE_URLS.get(provider)
    return ProviderConfig(provider=provider, api_key=api_key, base_url=base_url)
