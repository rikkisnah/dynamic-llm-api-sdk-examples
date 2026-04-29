"""Coverage for the chat-model filter and ranking helpers."""

from __future__ import annotations

import pytest

from llm_examples.domain_types import ModelInfo, ProviderName
from llm_examples.providers._common import is_chat_model, rank_chat_models


@pytest.mark.parametrize(
    "provider,model_id,expected",
    [
        # OpenAI / OCA (gpt/o-series + codex; pro variants blocked).
        ("openai", "gpt-4o-mini", True),
        ("openai", "gpt-4.1-mini", True),
        ("openai", "o3-mini", True),
        ("openai", "gpt-pro", False),
        ("oca", "gpt-5.5", True),
        ("oca", "oca/gpt-6.0-codex", True),
        # Claude requires "claude" in id; thinking variants stripped globally.
        ("claude", "claude-haiku-4-5", True),
        ("claude", "claude-sonnet-4-thinking", False),
        # Gemini stable allowlist.
        ("gemini", "gemini-2.5-flash", True),
        ("gemini", "gemini-2.5-pro", True),
        ("gemini", "gemini-2.5-flash-lite", True),
        ("gemini", "gemini-2.5-computer-use-preview-10-2025", False),
        ("gemini", "gemini-3.1-pro-preview-customtools", False),
        # DeepSeek: V4 chat variants are allowed; r1/reasoner are blocked.
        ("deepseek", "deepseek-chat", True),
        ("deepseek", "deepseek-v4-flash", True),
        ("deepseek", "deepseek-v4-pro", True),
        ("deepseek", "deepseek-reasoner", False),
        ("deepseek", "deepseek-r1", False),
        ("deepseek", "deepseek-chat-thinking", False),
        # Qwen: VL/OCR vision-only variants stripped.
        ("qwen", "qwen-plus", True),
        ("qwen", "qwen-vl-ocr-2025-11-20", False),
        # Z.ai: glm/zai prefix required.
        ("zai", "glm-4.6", True),
        ("zai", "glm-4.6-computer-use", False),
        # Global non-chat markers strip everything.
        ("openai", "text-embedding-3-large", False),
        ("openai", "whisper-1", False),
        ("openai", "tts-1", False),
    ],
)
def test_is_chat_model_per_provider(
    provider: ProviderName, model_id: str, expected: bool
) -> None:
    assert is_chat_model(provider, model_id) is expected


def test_rank_chat_models_filters_and_orders_newest_first() -> None:
    rows = [
        ModelInfo(provider="deepseek", id="deepseek-chat"),
        ModelInfo(provider="deepseek", id="deepseek-v4-flash"),
        ModelInfo(provider="deepseek", id="deepseek-v4-pro"),
        ModelInfo(provider="deepseek", id="deepseek-reasoner"),
    ]
    ranked = rank_chat_models(rows)
    ids = [m.id for m in ranked]
    assert "deepseek-reasoner" not in ids
    # V4 (newer version score) outranks V3 (`deepseek-chat`).
    assert ids[0].startswith("deepseek-v4")
    assert ids[-1] == "deepseek-chat"
