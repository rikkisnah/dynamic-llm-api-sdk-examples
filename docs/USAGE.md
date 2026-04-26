# Usage

## Providers

```bash
make providers
```

## List Models

```bash
make list P=openai
make list P=claude
make list P=gemini
make list P=deepseek
make list P=qwen
make list P=zai
```

## Run Prompt

```bash
make run-cli P=openai PROMPT="hello"
make run-cli P=claude M=claude-haiku-4-5 PROMPT="hello"
make run-cli P=gemini PROMPT="hello" MAX_TOKENS=128
```

Read prompt from file or stdin:

```bash
make run-file P=openai PROMPT_FILE=prompt.txt
make cli ARGS='run --provider openai --prompt-file -'
```

Streaming:

```bash
make run-stream P=openai PROMPT="hello"
```

JSON output:

```bash
make run-json P=openai PROMPT="hello"
make list-json P=openai
make providers-json
make check-conn-json P=openai
```

## Connection Check

```bash
make check-conn P=openai
```

## UI

```bash
make run PORT=8501
```

Chat page attachments:

1. Use `+` in the chat composer to attach files/images (or paste images where supported by browser/Streamlit).
2. Text files are injected into prompt context.
3. Images are forwarded as multimodal inputs to provider APIs (model must support vision).
4. Enable `Web research` in Chat settings to fetch live sources and include references in the current chat turn.
5. Web research is app-side retrieval (DuckDuckGo + Wikipedia), not MCP.
6. Assistant turns show explicit progress states while waiting on provider responses.

In the sidebar:

1. Select provider.
2. Select capability (`providers`, `list-models`, `run`, `check`).
3. Use the rendered controls from the same capability registry as CLI.

Web research failure behavior:

1. Chat warns in UI if source lookups fail.
2. Prompt still runs against your selected model without web context.
