# Usage

## Agent Workflows

```bash
# setup prompt template for Codex/Claude
cat INSTALL.md

# commit/push prompt template for Codex/Claude
cat CREATE-PR.md
```

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
make list P=oca
```

`list-models` filters non-chat models (embeddings, TTS, audio, vision-preview,
computer-use, customtools, thinking, reasoners) and ranks chat models
newest-first across all providers.

## Run Prompt

```bash
make run-cli P=openai PROMPT="hello"
make run-cli P=claude M=claude-haiku-4-5 PROMPT="hello"
make run-cli P=gemini PROMPT="hello" MAX_TOKENS=128
make run-cli P=oca PROMPT="hello"
```

`--provider` is optional. When omitted the CLI reads `AI_PROVIDER` /
`DEFAULT_AI_PROVIDER` from `.env` (alias-aware: e.g. `anthropic`/`claude`,
`codex`/`oca`):

```bash
AI_PROVIDER=oca make cli ARGS='run --prompt hello'
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

`make run` (and `make ui`) probes the requested port via
`scripts/find_free_port.py`. If `PORT` is in use, the next free TCP port in
`[PORT, PORT + PORT_SPAN)` (default span: 50) is used instead, and the chosen
port is logged. Override with `PORT_SPAN=` to widen or narrow the search.

Quote refresh behavior:

1. Clicking the quote refresh icon keeps the current page (`Chat`, `API`, or `Logs`).
2. API `TXT` output always includes a visible copy-ready code block.
3. API `run` response rendering matches chat: markdown output and long-response scrolling.
4. API `run` shows request progress states with elapsed time.

Chat page persistence:

1. Selected provider, selected chat model per provider, selected page, output mode, and prompt history are persisted to a gitignored `.state/llm_ui_state.json` so they survive Streamlit restarts and browser reloads.
2. Saved prompts are scoped per provider (one shared list for all models of that provider). When there is at least one saved prompt the picker + Send/Clear buttons render above the composer; otherwise the chat keeps its conversation-first layout.
3. `LLM_EXAMPLES_STATE_FILE=/path/to/state.json` overrides the location; `LLM_EXAMPLES_DISABLE_STATE=1` makes persistence a no-op (useful for ephemeral environments and unit tests).

Chat page attachments:

1. Use `+` in the chat composer to attach files/images (or paste images where supported by browser/Streamlit).
2. Text files are injected into prompt context.
3. Images are forwarded as multimodal inputs to provider APIs (model must support vision).
4. Enable `Web research` in Chat settings to fetch live sources and include references in the current chat turn.
5. Web research is app-side retrieval (DuckDuckGo + Wikipedia), not MCP.
6. Assistant turns show explicit progress states while waiting on provider responses.
7. Assistant replies preserve markdown formatting, use a scrollable view for long responses, and provide a `Copy response` raw-text section.

In the sidebar:

1. Select provider.
2. Select capability (`providers`, `list-models`, `run`, `check`).
3. Use the rendered controls from the same capability registry as CLI.

Web research failure behavior:

1. Chat warns in UI if source lookups fail.
2. Prompt still runs against your selected model without web context.
