"""Coverage for the env-loading and provider-resolution helpers in config.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_examples import config as config_module
from llm_examples.config import (
    DEFAULT_OCA_BASE_URL,
    DEFAULT_OCA_REASONING_EFFORT,
    codex_api_key,
    codex_auth_path,
    codex_client_headers,
    codex_reasoning_effort,
    env_int,
    env_value,
    explicit_provider_model,
    get_max_tokens,
    get_provider_config,
    normalize_provider_name,
    provider_env_names,
    provider_model_envs,
    resolve_default_provider,
)
from llm_examples.domain_types import MissingCredential
from llm_examples.registry import PROVIDERS


def test_env_value_skips_empty_and_quoted_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("__A__", "")
    monkeypatch.setenv("__B__", '"with quotes"')
    monkeypatch.setenv("__C__", "real")
    assert env_value("__A__", "__B__", "__C__") == "with quotes"
    monkeypatch.delenv("__B__", raising=False)
    assert env_value("__A__", "__C__") == "real"
    assert env_value("__A__") is None


def test_env_int_falls_back_on_unparseable_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("__INT__", "not-a-number")
    assert env_int(("__INT__",), 7) == 7
    monkeypatch.setenv("__INT__", "42")
    assert env_int(("__INT__",), 7) == 42
    monkeypatch.delenv("__INT__")
    assert env_int(("__INT__",), 7) == 7


def test_get_max_tokens_uses_first_set_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_MAX_TOKENS", raising=False)
    monkeypatch.delenv("MAX_TOKENS", raising=False)
    assert get_max_tokens() == config_module.DEFAULT_MAX_TOKENS
    monkeypatch.setenv("MAX_TOKENS", "256")
    assert get_max_tokens() == 256
    monkeypatch.setenv("AI_MAX_TOKENS", "1024")
    assert get_max_tokens() == 1024


def test_provider_env_metadata_helpers() -> None:
    assert provider_env_names("openai") == ("OPENAI_API_KEY", "OPENAI_BASE_URL")
    assert "ANTHROPIC_MODEL" in provider_model_envs("claude")
    assert "MODEL_CHAT" in provider_model_envs("oca")


def test_explicit_provider_model_chains_to_ai_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_CHAT", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    assert explicit_provider_model("openai") is None
    monkeypatch.setenv("AI_MODEL", "shared-model")
    assert explicit_provider_model("openai") == "shared-model"
    monkeypatch.setenv("OPENAI_MODEL", "specific-model")
    assert explicit_provider_model("openai") == "specific-model"


def test_normalize_provider_name_supports_aliases() -> None:
    assert normalize_provider_name("Anthropic") == "claude"
    assert normalize_provider_name("Z.ai") == "zai"
    assert normalize_provider_name("codex-oca") == "oca"
    assert normalize_provider_name("Codex (OCA)") == "oca"
    assert normalize_provider_name("garbage") is None
    assert normalize_provider_name("") is None
    assert normalize_provider_name(None) is None
    assert normalize_provider_name("   ") is None


def test_resolve_default_provider_uses_ai_provider_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "claude")
    monkeypatch.setenv("DEFAULT_AI_PROVIDER", "zai")
    assert resolve_default_provider(options=PROVIDERS, fallback="openai") == "claude"


def test_resolve_default_provider_falls_through_to_default_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("DEFAULT_AI_PROVIDER", "anthropic")
    assert resolve_default_provider(options=PROVIDERS, fallback="openai") == "claude"


def test_resolve_default_provider_falls_back_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("DEFAULT_AI_PROVIDER", raising=False)
    assert resolve_default_provider(options=PROVIDERS, fallback="openai") == "openai"


def test_resolve_default_provider_uses_first_option_when_fallback_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("DEFAULT_AI_PROVIDER", raising=False)
    options = ("claude", "openai")
    assert resolve_default_provider(options=options, fallback="zai") == "claude"  # type: ignore[arg-type]


def test_codex_auth_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"OPENAI_API_KEY": "from-auth-file"}), encoding="utf-8")
    monkeypatch.setenv("CODEX_AUTH_PATH", str(auth_file))
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    assert codex_auth_path() == auth_file
    assert codex_api_key() == "from-auth-file"


def test_codex_api_key_prefers_oca_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCA_API_KEY", "primary")
    monkeypatch.setenv("OCA_ACCESS_TOKEN", "secondary")
    assert codex_api_key() == "primary"
    monkeypatch.delenv("OCA_API_KEY")
    assert codex_api_key() == "secondary"


def test_codex_api_key_returns_none_for_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("CODEX_AUTH_PATH", "/tmp/__definitely_missing__.json")
    assert codex_api_key() is None


def test_codex_api_key_handles_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("CODEX_AUTH_PATH", str(auth_file))
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    assert codex_api_key() is None


def test_codex_api_key_handles_non_dict_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "auth.json"
    auth_file.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setenv("CODEX_AUTH_PATH", str(auth_file))
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    assert codex_api_key() is None


def test_codex_api_key_handles_non_string_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"OPENAI_API_KEY": 1234}), encoding="utf-8")
    monkeypatch.setenv("CODEX_AUTH_PATH", str(auth_file))
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    assert codex_api_key() is None


def test_codex_auth_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_AUTH_PATH", raising=False)
    assert codex_auth_path() == Path.home() / ".codex" / "auth.json"


def test_codex_reasoning_effort_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REASONING_EFFORT", raising=False)
    assert codex_reasoning_effort() == DEFAULT_OCA_REASONING_EFFORT


def test_codex_reasoning_effort_explicit_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REASONING_EFFORT", "high")
    assert codex_reasoning_effort() == "high"


def test_codex_reasoning_effort_blank_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REASONING_EFFORT", "   ")
    assert codex_reasoning_effort() is None


def test_codex_client_headers_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OCA_CLIENT_HEADER", raising=False)
    monkeypatch.delenv("OCA_CLIENT_VERSION", raising=False)
    headers = codex_client_headers()
    assert headers == {"client": "codex-cli", "client-version": "1.0"}


def test_codex_client_headers_respects_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCA_CLIENT_HEADER", "vscode")
    monkeypatch.setenv("OCA_CLIENT_VERSION", "9.9")
    headers = codex_client_headers()
    assert headers["client"] == "vscode"
    assert headers["client-version"] == "9.9"


def test_get_provider_config_for_oca_falls_back_to_default_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"OPENAI_API_KEY": "from-auth"}), encoding="utf-8")
    monkeypatch.setenv("CODEX_AUTH_PATH", str(auth_file))
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("OCA_BASE_URL", raising=False)
    cfg = get_provider_config("oca")
    assert cfg.api_key == "from-auth"
    assert cfg.base_url == DEFAULT_OCA_BASE_URL


def test_get_provider_config_for_oca_raises_when_no_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCA_API_KEY", raising=False)
    monkeypatch.delenv("OCA_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("CODEX_AUTH_PATH", "/tmp/__missing_oca_auth__.json")
    with pytest.raises(MissingCredential):
        get_provider_config("oca")


def test_load_dotenv_reads_from_package_and_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    (package_dir / ".env").write_text(
        "# comment\nexport FROM_PACKAGE=\"package-value\"\nALPHA=pkg-alpha\nbroken\n=ignored\n",
        encoding="utf-8",
    )
    (root_dir / ".env").write_text(
        "FROM_ROOT='root-value'\nALPHA=root-alpha\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_PACKAGE_DIR", package_dir)
    monkeypatch.setattr(config_module, "_REPO_ROOT", root_dir)
    monkeypatch.setattr(config_module, "_dotenv_loader", lambda *_a, **_k: True)
    monkeypatch.delenv("FROM_PACKAGE", raising=False)
    monkeypatch.delenv("FROM_ROOT", raising=False)
    monkeypatch.delenv("ALPHA", raising=False)
    config_module._ENV_FILE_KEYS.clear()
    assert config_module._load_dotenv() is True
    import os

    assert os.environ["FROM_PACKAGE"] == "package-value"
    assert os.environ["FROM_ROOT"] == "root-value"
    # Root .env overrides previously file-loaded values.
    assert os.environ["ALPHA"] == "root-alpha"


def test_fallback_load_dotenv_returns_false() -> None:
    assert config_module._fallback_load_dotenv() is False


def test_apply_env_file_overrides_only_file_loaded_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    one = tmp_path / "one.env"
    one.write_text("ALPHA=first\nBETA=first-beta\n", encoding="utf-8")
    two = tmp_path / "two.env"
    two.write_text("ALPHA=second\nGAMMA=process-set\n", encoding="utf-8")
    monkeypatch.delenv("ALPHA", raising=False)
    monkeypatch.delenv("BETA", raising=False)
    monkeypatch.setenv("GAMMA", "process-wins")
    config_module._ENV_FILE_KEYS.clear()
    config_module._apply_env_file(one, override_file_values=False)
    config_module._apply_env_file(two, override_file_values=True)
    import os

    assert os.environ["ALPHA"] == "second"
    assert os.environ["BETA"] == "first-beta"
    assert os.environ["GAMMA"] == "process-wins"


def test_read_dotenv_pairs_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert config_module._read_dotenv_pairs(tmp_path / "nope.env") == []


def test_apply_env_file_skips_empty_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "blank.env"
    target.write_text("EMPTY=\nFILLED=keep\n", encoding="utf-8")
    monkeypatch.delenv("EMPTY", raising=False)
    monkeypatch.delenv("FILLED", raising=False)
    config_module._ENV_FILE_KEYS.clear()
    config_module._apply_env_file(target, override_file_values=False)
    import os

    assert "EMPTY" not in os.environ
    assert os.environ["FILLED"] == "keep"
