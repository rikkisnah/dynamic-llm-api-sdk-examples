"""Codex / OCA standalone example using the OpenAI SDK against the LiteLLM proxy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_MODEL = "gpt-5.5"
DEFAULT_BASE_URL = (
    "https://code-internal.aiservice.us-chicago-1.oci.oraclecloud.com/20250206/app/litellm"
)


def _resolve_api_key() -> str:
    for env_name in ("OCA_API_KEY", "OCA_ACCESS_TOKEN"):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    auth_path = Path(os.getenv("CODEX_AUTH_PATH", "").strip() or "~/.codex/auth.json").expanduser()
    if auth_path.is_file():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception:
            return ""
        if isinstance(data, dict):
            value = data.get("OPENAI_API_KEY")
            if isinstance(value, str):
                return value.strip()
    return ""


def build_client(api_key: str, base_url: str | None) -> object:
    from openai import OpenAI  # type: ignore[import-not-found]

    return OpenAI(
        api_key=api_key,
        base_url=base_url or DEFAULT_BASE_URL,
        default_headers={
            "client": os.getenv("OCA_CLIENT_HEADER", "codex-cli"),
            "client-version": os.getenv("OCA_CLIENT_VERSION", "1.0"),
        },
    )


def list_models(client: object) -> list[str]:
    models_obj = getattr(client, "models", None)
    if models_obj is None:
        return [DEFAULT_MODEL]
    try:
        payload = models_obj.list()
    except Exception:
        return [DEFAULT_MODEL]
    data = getattr(payload, "data", payload)
    ids: list[str] = []
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if isinstance(model_id, str):
                ids.append(model_id)
    return ids or [DEFAULT_MODEL]


def run_prompt(client: object, model: str, prompt: str) -> str:
    kwargs: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 64,
    }
    effort = os.getenv("REASONING_EFFORT", "xhigh").strip()
    if effort:
        kwargs["reasoning_effort"] = effort
    response = client.chat.completions.create(**kwargs)
    choices = getattr(response, "choices", [])
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    return ""


def main() -> int:
    api_key = _resolve_api_key()
    if not api_key:
        print("Missing OCA_API_KEY (and no ~/.codex/auth.json found)", file=sys.stderr)
        return 2
    base_url = os.getenv("OCA_BASE_URL", "").strip() or None
    client = build_client(api_key, base_url)
    models = list_models(client)
    model = models[0] if models else DEFAULT_MODEL
    print(f"OCA models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    print(run_prompt(client, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
