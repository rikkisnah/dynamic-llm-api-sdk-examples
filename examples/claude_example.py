"""Claude standalone SDK example."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "claude-haiku-4-5"


def build_client(api_key: str, base_url: str | None) -> object:
    from anthropic import Anthropic  # type: ignore[import-not-found]

    kwargs: dict[str, object] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return Anthropic(**kwargs)


def list_models(client: object) -> list[str]:
    models_obj = getattr(client, "models", None)
    list_fn = getattr(models_obj, "list", None)
    if not callable(list_fn):
        return [DEFAULT_MODEL, "claude-sonnet-4-5"]
    payload = list_fn()
    data = getattr(payload, "data", payload)
    ids: list[str] = []
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if isinstance(model_id, str):
                ids.append(model_id)
    return ids or [DEFAULT_MODEL, "claude-sonnet-4-5"]


def run_prompt(client: object, model: str, prompt: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
    )
    content = getattr(response, "content", [])
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def main() -> int:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("Missing ANTHROPIC_API_KEY", file=sys.stderr)
        return 2
    client = build_client(api_key, os.getenv("ANTHROPIC_BASE_URL", "").strip() or None)
    models = list_models(client)
    model = models[0]
    print(f"Claude models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    print(run_prompt(client, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
