"""Z.ai standalone SDK example with HTTP fallback."""

from __future__ import annotations

import os
import sys

DEFAULT_MODEL = "glm-4.6"


def build_sdk_client(api_key: str, base_url: str | None) -> object | None:
    try:
        from zai import Client as ZAIClient  # type: ignore[import-not-found]
    except Exception:
        return None
    kwargs: dict[str, object] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return ZAIClient(**kwargs)


def list_models(api_key: str, base_url: str) -> list[str]:
    import httpx

    with httpx.Client(base_url=base_url.rstrip("/"), headers={"Authorization": f"Bearer {api_key}"}) as http:
        try:
            response = http.get("/models")
            response.raise_for_status()
            data = response.json().get("data")
            ids: list[str] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        model_id = item.get("id")
                        if isinstance(model_id, str):
                            ids.append(model_id)
            if ids:
                return ids
        except Exception:
            return [DEFAULT_MODEL, "glm-4.5-air"]
    return [DEFAULT_MODEL, "glm-4.5-air"]


def run_prompt_sdk(client: object, model: str, prompt: str) -> str:
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


def run_prompt_http(api_key: str, base_url: str, model: str, prompt: str) -> str:
    import httpx

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 64,
    }
    with httpx.Client(base_url=base_url.rstrip("/"), headers={"Authorization": f"Bearer {api_key}"}) as http:
        response = http.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
    return ""


def main() -> int:
    api_key = os.getenv("ZAI_API_KEY", "").strip()
    if not api_key:
        print("Missing ZAI_API_KEY", file=sys.stderr)
        return 2
    base_url = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4").strip()
    client = build_sdk_client(api_key, base_url)
    models = list_models(api_key, base_url)
    model = models[0]
    print(f"Z.ai models: {', '.join(models[:5])}")
    print(f"Using model: {model}")
    if client is not None:
        print(run_prompt_sdk(client, model, "Say hello in one short sentence."))
    else:
        print(run_prompt_http(api_key, base_url, model, "Say hello in one short sentence."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
