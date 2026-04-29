# Standalone SDK Examples

Each script in this folder is self-contained and does **not** import `llm_examples`.

These scripts are documentation-grade examples: when provider behavior changes in
package adapters, keep the corresponding standalone example in sync.

Run one example:

```bash
uv run python examples/openai_example.py
```

Available scripts:

- `examples/openai_example.py`
- `examples/claude_example.py`
- `examples/gemini_example.py` (OpenAI-compatible Gemini endpoint)
- `examples/deepseek_example.py`
- `examples/qwen_example.py`
- `examples/zai_example.py`
- `examples/oca_example.py` (Codex / OCA via LiteLLM proxy)
