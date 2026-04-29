"""Gemini standalone example using the OpenAI-compatible endpoint."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


def build_client(api_key: str, base_url: str | None) -> object:
    from openai import OpenAI  # type: ignore[import-not-found]

    return OpenAI(api_key=api_key, base_url=base_url or DEFAULT_BASE_URL)


def list_models(client: object) -> list[str]:
    models_obj = getattr(client, "models", None)
    if models_obj is None:
        return [DEFAULT_MODEL, "gemini-2.5-pro"]
    try:
        payload = models_obj.list()
    except Exception:
        return [DEFAULT_MODEL, "gemini-2.5-pro"]
    data = getattr(payload, "data", payload)
    ids: list[str] = []
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None) or getattr(item, "name", None)
            if isinstance(model_id, str):
                ids.append(model_id.removeprefix("models/"))
    return ids or [DEFAULT_MODEL, "gemini-2.5-pro"]


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
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        return 2
    base_url = os.getenv("GEMINI_BASE_URL", "").strip() or None
    client = build_client(api_key, base_url)
    models = list_models(client)
    model = models[0] if models else DEFAULT_MODEL
    print(f"Gemini models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    print(run_prompt(client, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
