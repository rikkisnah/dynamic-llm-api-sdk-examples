# dynamic-llm-api-sdk-examples

Dynamic multi-provider LLM SDK examples with strict CLI and Streamlit parity.

Supported providers:

| Provider | Docs | Default API Base URL |
|---|---|---|
| OpenAI | [platform.openai.com/docs](https://platform.openai.com/docs) | `https://api.openai.com/v1` |
| Claude (Anthropic) | [docs.anthropic.com](https://docs.anthropic.com) | `https://api.anthropic.com` |
| Gemini (Google) | [ai.google.dev/docs](https://ai.google.dev/docs) | `https://generativelanguage.googleapis.com` |
| DeepSeek | [api-docs.deepseek.com](https://api-docs.deepseek.com) | `https://api.deepseek.com` |
| Qwen (DashScope OpenAI-compatible) | [dashscope.aliyun.com](https://dashscope.aliyun.com) | `https://dashscope-us.aliyuncs.com/compatible-mode/v1` |
| Z.ai | [docs.z.ai](https://docs.z.ai) | `https://api.z.ai/api/paas/v4` |

## Quickstart

```bash
cp .env.example .env
make setup
make check
```

Makefile is the primary way to run everything. See all commands:

```bash
make help
```

## Agent Prompts

These files are prompt templates intended for Codex/Claude users:

- [INSTALL.md](INSTALL.md): setup/install workflow for Ubuntu and macOS.
- [CREATE-PR.md](CREATE-PR.md): docs-sync + validate + commit + push workflow on `main`.

## Documentation Sync Contract

When behavior changes, keep these docs aligned in the same commit:

- `README.md`
- `CLAUDE.md` (`AGENTS.md` symlink)
- `docs/USAGE.md`
- `docs/HOW-IT-WORKS.md`
- `INSTALL.md`
- `CREATE-PR.md`

## Make Targets

Common targets:

- `make setup`: install app + dev dependencies with `uv`
- `make run`: start Streamlit UI (default port `8501`)
- `make providers`: list configured providers
- `make list P=openai`: list models for provider
- `make run-cli P=openai PROMPT="hello"`: run a CLI prompt
- `make run-cli P=openai PROMPT="hello" OUT=json`: run a CLI prompt as JSON (`OUT=txt` for plain text)
- `make run-stream P=openai PROMPT="hello"`: run with streaming
- `make check-conn P=openai`: validate credentials for one provider
- `make test-llm-all`: live connection + deterministic hello prompt across all 6 providers
- `make check`: run lint, import checks, typing, tests, and architecture score

Use `make help` for the complete grouped list, including JSON and passthrough targets.

Run CLI (make wrappers):

```bash
make providers
make list P=openai
make run-cli P=openai PROMPT="hello"
make run-cli P=openai PROMPT="hello" OUT=json
make run-stream P=openai PROMPT="hello"
make run-stream P=openai PROMPT="hello" OUT=json
make check-conn P=openai
make check-conn P=openai OUT=json
make list P=openai OUT=json
make providers OUT=json
```

CLI version:

```bash
uv run llm-examples --version
```

Live provider regression check:

```bash
make test-llm-all
# optional overrides:
# make test-llm-all HELLO_PROMPT="Reply with exactly: Hello world" HELLO_MAX_TOKENS=64 HELLO_MAX_TOKENS_ZAI=512
```

Note: Z.ai models can consume output tokens for reasoning first; low `MAX_TOKENS` may yield empty final text.
Note: Z.ai adapter auto-continues when it hits a token-limit finish with non-empty text so long answers can continue seamlessly in CLI and UI (including stream mode).
Note: OpenAI reasoning-heavy models (for example `gpt-5-mini`) can also consume token budget before producing visible text; the OpenAI adapter now retries once with a higher token budget when it detects this empty token-limit response pattern.

Run UI:

```bash
make run PORT=8501
```

UI defaults:

- Dark theme is always enabled.
- Version is shown in the UI header and sidebar.
- A single-line quote banner is shown at the top of the page (famous/funny/Bible/Hindu-epic rotation) with a `Refresh quote` icon control.
- Refreshing the quote keeps the current page selection (`API`/`Chat`/`Logs`) instead of jumping surfaces.
- A sidebar call log records all Streamlit-triggered provider calls (start/success/error).
- A visible `Output format` toggle (`TXT` or `JSON`) lets every UI call render in either mode.
- Sidebar has a `Page` switch (`API` / `Chat` / `Logs`).
- Run form model is chosen from the provider model list (no manual model text entry).
- Run form keeps recent prompts with `Saved prompts` selector and `Clear saved prompts`.
- API `TXT` outputs now include visible copy-ready blocks (with one-click copy) across `providers`, `list-models`, `run`, and `check`.
- API `run` responses follow chat-style rendering: markdown display and long-response scrolling.
- API `run` now shows explicit progress states (`calling`, `streaming/generating`, `completed`) with elapsed time.
- Chat page keeps memory per `provider + model` thread, with explicit `Clear chat history`.
- Chat keeps recent prompts with `Saved prompts` selector, `Send saved prompt`, and `Clear saved prompts`.
- Chat is conversation-first (ChatGPT-style): history and composer stay primary, while prompt/file/stream controls stay in collapsed `Chat settings`.
- Chat settings include a `Web research` toggle that fetches DuckDuckGo + Wikipedia sources and injects summarized references into the current turn (no MCP dependency).
- Chat replies render with markdown formatting, and long replies are shown in a bounded scrollable panel.
- Every assistant reply includes a `Copy response` section with raw text for reliable copy/paste.
- Chat now shows explicit turn progress states (`calling`, `streaming/generating`, `completed`) with elapsed time so long-running calls are visibly active.
- Use the chat composer `+` button to attach files/images per message (and paste images where browser clipboard upload is supported).
- Attached text files are injected into prompt context for that turn.
- Attached images are forwarded to provider multimodal APIs for OpenAI, Claude, Gemini, DeepSeek, Qwen, and Z.ai (model support still depends on the selected model).
- Non-image binary files remain metadata-only notes.

## Commands

| Command | CLI | UI |
|---|---|---|
| `providers` | `make providers` | Sidebar provider status table |
| `list-models` | `make list P=<provider>` | `List models` action |
| `run` | `make run-cli P=<provider> PROMPT="..." [M=...] [SYSTEM=...] [MAX_TOKENS=...]` | Prompt form |
| `check` | `make check-conn P=<provider>` | `Check credentials` action |

Every Make API target supports `OUT=txt|json` (`txt` default). JSON wrappers remain available (`make providers-json`, `make list-json`, `make run-json`, `make check-conn-json`) and generic passthrough is available via `make cli ARGS='...'`.

Web research invocation is UI-chat only and provider-agnostic: the app fetches sources itself, then sends summarized context to the selected provider in the same prompt.

## Env Vars

| Provider | API key env | Base URL env |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Claude | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Gemini | `GEMINI_API_KEY` | — |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL` |
| Qwen | `DASHSCOPE_API_KEY` | `DASHSCOPE_BASE_URL` |
| Z.ai | `ZAI_API_KEY` | `ZAI_BASE_URL` |

## Parity Matrix

| Capability | Parameters |
|---|---|
| `providers` | — |
| `list-models` | `provider` |
| `run` | `provider`, `model`, `prompt`/`prompt-file`, `system`, `max-tokens`, `stream` |
| `check` | `provider` |

## Layout

- Main package: `llm_examples/`
- Standalone SDK scripts: `examples/*.py`
- ADRs and implementation docs: `docs/`

## Docs

- [INSTALL.md](INSTALL.md)
- [CREATE-PR.md](CREATE-PR.md)
- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)
- [examples/README.md](examples/README.md)
