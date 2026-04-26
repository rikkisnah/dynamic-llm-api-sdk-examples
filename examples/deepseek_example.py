"""DeepSeek standalone example via OpenAI-compatible SDK path."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "deepseek-chat"


def build_client(api_key: str, base_url: str) -> object:
    from openai import OpenAI  # type: ignore[import-not-found]

    return OpenAI(api_key=api_key, base_url=base_url)


def list_models(client: object) -> list[str]:
    try:
        payload = client.models.list()
    except Exception:
        return [DEFAULT_MODEL, "deepseek-reasoner"]
    data = getattr(payload, "data", payload)
    ids: list[str] = []
    if isinstance(data, list):
        for item in data:
            model_id = getattr(item, "id", None)
            if isinstance(model_id, str):
                ids.append(model_id)
    return ids or [DEFAULT_MODEL, "deepseek-reasoner"]


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
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Missing DEEPSEEK_API_KEY", file=sys.stderr)
        return 2
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com"
    client = build_client(api_key, base_url)
    models = list_models(client)
    model = models[0]
    print(f"DeepSeek models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    print(run_prompt(client, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
