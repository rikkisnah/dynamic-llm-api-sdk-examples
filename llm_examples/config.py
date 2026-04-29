"""Tier 0: Environment-driven provider configuration loading."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path

from llm_examples.domain_types import MissingCredential, ProviderConfig, ProviderName

PACKAGE_NAME = "dynamic-llm-api-sdk-examples"
DEFAULT_OCA_BASE_URL = (
    "https://code-internal.aiservice.us-chicago-1.oci.oraclecloud.com/20250206/app/litellm"
)
DEFAULT_OCA_REASONING_EFFORT = "xhigh"
DEFAULT_MAX_TOKENS = 512


def _fallback_load_dotenv(*_args: object, **_kwargs: object) -> bool:
    return False


_dotenv_loader: Callable[..., bool]
try:
    from dotenv import load_dotenv as _load_dotenv_impl
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs
    _dotenv_loader = _fallback_load_dotenv
else:
    _dotenv_loader = _load_dotenv_impl


_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent

_ENV_FILE_KEYS: set[str] = set()


def _read_dotenv_pairs(path: Path) -> list[tuple[str, str]]:
    """Parse a .env file into (key, value) pairs without touching the environment."""
    if not path.exists():
        return []
    rows: list[tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            continue
        rows.append((key, value))
    return rows


def _apply_env_file(path: Path, *, override_file_values: bool) -> None:
    """Apply key/value pairs from a .env file with file-vs-process precedence rules."""
    for key, value in _read_dotenv_pairs(path):
        if not value:
            continue
        if key not in os.environ:
            os.environ[key] = value
            _ENV_FILE_KEYS.add(key)
            continue
        if override_file_values and key in _ENV_FILE_KEYS:
            os.environ[key] = value


def _load_dotenv() -> bool:
    """Load `.env` files from the package and repo root.

    Process environment values always win. Among files, the repo-root `.env`
    overrides previously file-loaded values from the package-level `.env`.
    """
    package_env = _PACKAGE_DIR / ".env"
    root_env = _REPO_ROOT / ".env"
    _apply_env_file(package_env, override_file_values=False)
    _apply_env_file(root_env, override_file_values=True)
    # Run python-dotenv (if available) so consumers exporting via library calls
    # also benefit; treat its return value as informational only.
    return bool(_dotenv_loader())


_load_dotenv()

_ENV_KEYS: Mapping[ProviderName, tuple[str, str | None]] = {
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "claude": ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_BASE_URL"),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "qwen": ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL"),
    "zai": ("ZAI_API_KEY", "ZAI_BASE_URL"),
    "oca": ("OCA_API_KEY", "OCA_BASE_URL"),
}

_DEFAULT_BASE_URLS: Mapping[ProviderName, str] = {
    "deepseek": "https://api.deepseek.com",
    "zai": "https://api.z.ai/api/paas/v4",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "qwen": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    "oca": DEFAULT_OCA_BASE_URL,
}

PROVIDER_MODEL_ENVS: Mapping[ProviderName, tuple[str, ...]] = {
    "openai": ("OPENAI_MODEL", "OPENAI_MODEL_CHAT"),
    "claude": ("ANTHROPIC_MODEL", "CLAUDE_MODEL", "CLAUDE_CHAT_MODEL"),
    "gemini": ("GEMINI_MODEL",),
    "deepseek": ("DEEPSEEK_MODEL",),
    "qwen": ("QWEN_MODEL", "DASHSCOPE_MODEL"),
    "zai": ("ZAI_MODEL", "Z_AI_MODEL"),
    "oca": ("OCA_MODEL", "MODEL_CHAT"),
}

_PROVIDER_ALIASES: Mapping[str, ProviderName] = {
    "openai": "openai",
    "anthropic": "claude",
    "claude": "claude",
    "gemini": "gemini",
    "google": "gemini",
    "deepseek": "deepseek",
    "qwen": "qwen",
    "dashscope": "qwen",
    "zai": "zai",
    "z.ai": "zai",
    "z-ai": "zai",
    "oca": "oca",
    "codex": "oca",
    "codex-oca": "oca",
    "codex(oca)": "oca",
    "codex (oca)": "oca",
}


def env_value(*names: str) -> str | None:
    """Return the first non-empty value among the named environment variables."""
    for name in names:
        value = os.environ.get(name, "").strip().strip("\"'")
        if value:
            return value
    return None


def env_int(names: tuple[str, ...], default: int) -> int:
    """Return an integer from the first parseable env var or the default."""
    raw = env_value(*names)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_max_tokens(default: int = DEFAULT_MAX_TOKENS) -> int:
    """Resolve max-token budget from `AI_MAX_TOKENS` / `MAX_TOKENS` env vars."""
    return env_int(("AI_MAX_TOKENS", "MAX_TOKENS"), default)


def provider_env_names(provider: ProviderName) -> tuple[str, str | None]:
    """Return (api_key_env, base_url_env) for a provider."""
    return _ENV_KEYS[provider]


def provider_model_envs(provider: ProviderName) -> tuple[str, ...]:
    """Return the ordered model-env aliases for a provider."""
    return PROVIDER_MODEL_ENVS[provider]


def explicit_provider_model(provider: ProviderName) -> str | None:
    """Return the configured model env value for a provider (with `AI_MODEL` fallback)."""
    return env_value(*provider_model_envs(provider), "AI_MODEL")


def normalize_provider_name(value: str | None) -> ProviderName | None:
    """Normalize a free-form provider label to a canonical `ProviderName`."""
    if not value:
        return None
    key = value.strip().lower()
    if not key:
        return None
    if key in _PROVIDER_ALIASES:
        return _PROVIDER_ALIASES[key]
    compact = "".join(ch for ch in key if ch.isalnum() or ch in {".", "-"})
    return _PROVIDER_ALIASES.get(compact)


def resolve_default_provider(
    *, options: tuple[ProviderName, ...], fallback: ProviderName
) -> ProviderName:
    """Resolve the default provider from `AI_PROVIDER` / `DEFAULT_AI_PROVIDER`."""
    for env_name in ("AI_PROVIDER", "DEFAULT_AI_PROVIDER"):
        candidate = normalize_provider_name(os.environ.get(env_name))
        if candidate is not None and candidate in options:
            return candidate
    return fallback if fallback in options else options[0]


def codex_auth_path() -> Path:
    """Resolve the Codex auth.json path (`CODEX_AUTH_PATH` override supported)."""
    raw = os.environ.get("CODEX_AUTH_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".codex" / "auth.json"


def _read_codex_auth() -> Mapping[str, object]:
    path = codex_auth_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def codex_api_key() -> str | None:
    """Resolve the OCA / Codex API key from env or `~/.codex/auth.json`."""
    if key := env_value("OCA_API_KEY", "OCA_ACCESS_TOKEN"):
        return key
    raw = _read_codex_auth().get("OPENAI_API_KEY")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def codex_reasoning_effort() -> str | None:
    """Return the reasoning-effort value to send to OCA, or None to omit."""
    if "REASONING_EFFORT" not in os.environ:
        return DEFAULT_OCA_REASONING_EFFORT
    raw = os.environ["REASONING_EFFORT"].strip()
    return raw or None


def codex_client_headers() -> dict[str, str]:
    """Build the custom headers used when talking to the OCA proxy."""
    return {
        "client": os.environ.get("OCA_CLIENT_HEADER", "codex-cli"),
        "client-version": os.environ.get("OCA_CLIENT_VERSION", "1.0"),
    }


def get_provider_config(provider: ProviderName) -> ProviderConfig:
    """Resolve provider configuration from current process environment."""
    if provider == "oca":
        oca_key = codex_api_key()
        if not oca_key:
            raise MissingCredential(provider=provider, env_var="OCA_API_KEY")
        oca_base = env_value("OCA_BASE_URL") or DEFAULT_OCA_BASE_URL
        return ProviderConfig(provider=provider, api_key=oca_key, base_url=oca_base)

    api_key_env, base_url_env = provider_env_names(provider)
    api_key = os.environ.get(api_key_env, "").strip().strip("\"'")
    if not api_key:
        raise MissingCredential(provider=provider, env_var=api_key_env)

    base_url: str | None = _DEFAULT_BASE_URLS.get(provider)
    if base_url_env is not None:
        configured = os.environ.get(base_url_env, "").strip().strip("\"'")
        if configured:
            base_url = configured
    return ProviderConfig(provider=provider, api_key=api_key, base_url=base_url)


def get_app_version() -> str:
    """Resolve package version for CLI/UI display."""
    try:
        value = _package_version(PACKAGE_NAME)
        return value if isinstance(value, str) and value else "0.0.0"
    except PackageNotFoundError:
        return "0.0.0"
