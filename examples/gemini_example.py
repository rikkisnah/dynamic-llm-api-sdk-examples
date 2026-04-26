"""Gemini standalone SDK example using google-genai."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "gemini-2.5-flash"


def build_client(api_key: str) -> object:
    from google import genai  # type: ignore[import-not-found]

    return genai.Client(api_key=api_key)


def list_models(client: object) -> list[str]:
    try:
        payload = client.models.list()
    except Exception:
        return [DEFAULT_MODEL, "gemini-2.5-pro"]
    ids: list[str] = []
    for item in payload:
        name = getattr(item, "name", None)
        if isinstance(name, str):
            ids.append(name)
    return ids or [DEFAULT_MODEL, "gemini-2.5-pro"]


def run_prompt(client: object, model: str, prompt: str) -> str:
    response = client.models.generate_content(model=model, contents=prompt, config={"max_output_tokens": 64})
    text = getattr(response, "text", None)
    return text if isinstance(text, str) else ""


def main() -> int:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        return 2
    client = build_client(api_key)
    models = list_models(client)
    model = models[0]
    print(f"Gemini models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    print(run_prompt(client, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
