# dynamic-llm-api-sdk-examples

Dynamic multi-provider LLM SDK examples with strict CLI and Streamlit parity.

Supported providers:

- OpenAI
- Claude (Anthropic)
- Gemini (Google)
- DeepSeek
- Qwen (DashScope)
- Z.ai

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

Run CLI (make wrappers):

```bash
make providers
make list P=openai
make run-cli P=openai PROMPT="hello"
make run-stream P=openai PROMPT="hello"
make check-conn P=openai
```

Run UI:

```bash
make run PORT=8501
```

UI defaults:

- Dark theme is always enabled.
- A quote banner is shown at the top of the page (famous/funny/Bible/Hindu-epic rotation).

## Commands

| Command | CLI | UI |
|---|---|---|
| `providers` | `make providers` | Sidebar provider status table |
| `list-models` | `make list P=<provider>` | `List models` action |
| `run` | `make run-cli P=<provider> PROMPT="..." [M=...] [SYSTEM=...] [MAX_TOKENS=...]` | Prompt form |
| `check` | `make check-conn P=<provider>` | `Check credentials` action |

JSON wrappers are available (`make providers-json`, `make list-json`, `make run-json`, `make check-conn-json`) and generic passthrough is available via `make cli ARGS='...'`.

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

- [docs/PLAN.md](docs/PLAN.md)
- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)
- [examples/README.md](examples/README.md)
