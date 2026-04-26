"""OpenAI standalone SDK example."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "gpt-4o-mini"


def build_client(api_key: str, base_url: str | None) -> object:
    from openai import OpenAI  # type: ignore[import-not-found]

    kwargs: dict[str, object] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def list_models(client: object) -> list[str]:
    models_obj = getattr(client, "models", None)
    if models_obj is None:
        return [DEFAULT_MODEL]
    payload = models_obj.list()
    data = getattr(payload, "data", payload)
    ids: list[str] = []
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if isinstance(model_id, str):
                ids.append(model_id)
    return ids or [DEFAULT_MODEL]


def run_prompt(client: object, model: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
    )
    choices = getattr(response, "choices", [])
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    return ""


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Missing OPENAI_API_KEY", file=sys.stderr)
        return 2
    client = build_client(api_key, os.getenv("OPENAI_BASE_URL", "").strip() or None)
    models = list_models(client)
    model = models[0] if models else DEFAULT_MODEL
    print(f"OpenAI models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    text = run_prompt(client, model, "Say hello in one short sentence.")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
