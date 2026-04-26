"""Qwen standalone DashScope SDK example."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "qwen-plus"


def generation_class() -> object:
    from dashscope import Generation  # type: ignore[import-not-found]

    return Generation


def list_models() -> list[str]:
    return [DEFAULT_MODEL, "qwen-turbo"]


def run_prompt(model: str, prompt: str, api_key: str, base_url: str | None) -> str:
    generation = generation_class()
    kwargs: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "api_key": api_key,
        "result_format": "message",
        "max_tokens": 64,
    }
    if base_url:
        kwargs["base_url"] = base_url
    response = generation.call(**kwargs)
    output = getattr(response, "output", response)
    choices = getattr(output, "choices", [])
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
    return ""


def main() -> int:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        print("Missing DASHSCOPE_API_KEY", file=sys.stderr)
        return 2
    base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip() or None
    models = list_models()
    model = models[0]
    print(f"Qwen models: {', '.join(models)}")
    print(f"Using model: {model}")
    print(run_prompt(model, "Say hello in one short sentence.", api_key, base_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
