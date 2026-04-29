# How It Works

## Tiered Architecture

1. Tier 0: domain/config/capability types
2. Tier 1: provider interface (`BaseClient`)
3. Tier 2: provider adapters (one per provider, plus shared `_common.py` helpers)
4. Tier 3: provider registry
5. Tier 4: service layer
6. Tier 5: CLI and Streamlit surfaces

UI and CLI only call `llm_examples.services`.

## Configuration Loading

`llm_examples.config` loads `.env` from two locations: the repo root and
`llm_examples/.env`. Process environment variables always win; the repo-root
`.env` overrides values that came from `llm_examples/.env`. The same module
exposes `resolve_default_provider`, `explicit_provider_model`, `get_max_tokens`,
and OCA helpers (`codex_api_key`, `codex_reasoning_effort`,
`codex_client_headers`, `codex_auth_path`).

## Provider Resolution

Provider selection follows this precedence:

1. The CLI flag `--provider` or the UI sidebar selection.
2. `AI_PROVIDER` env var (case-insensitive, supports aliases such as
   `anthropic`/`claude`, `codex`/`oca`, `z.ai`/`zai`).
3. `DEFAULT_AI_PROVIDER` env var.
4. The compiled-in fallback (`openai`).

Model selection per provider follows: explicit `--model` → provider-specific
env var (e.g. `OPENAI_MODEL`, `OPENAI_MODEL_CHAT`) → generic `AI_MODEL` →
provider's hard-coded default model.

## Request Lifecycle

1. CLI or UI collects provider/model/prompt.
2. UI chat can optionally add attachment context and web-research context for the turn.
3. Service layer builds `ChatRequest` (including optional `image_attachments`).
4. Registry resolves provider adapter.
5. Provider adapter calls native SDK (or documented fallback).
6. Provider response is normalized into `ChatResponse`.
7. Surface renders text and metadata.
8. Chat assistant rendering keeps markdown formatting, enables scroll for long replies, and exposes raw-text copy blocks.

## Chat Attachments and Multimodal Flow

1. Chat composer accepts uploaded files/images (`+`) and pasted images where browser/Streamlit supports it.
2. Text files are normalized into prompt context text.
3. Images are normalized into `ImageAttachment` objects.
4. Provider adapters map those attachments to provider-native multimodal payloads:
   - OpenAI-compatible (OpenAI, Gemini, DeepSeek, Qwen, Z.ai, OCA)
   - Anthropic blocks (Claude)
5. If a selected model does not support vision, provider adapters return normalized errors.

## Model List Filtering and Ranking

`ProviderClientBase.list_models` runs every provider's listed models through
`is_chat_model(provider, model_id)` and `rank_chat_models`. The filter:

- Drops markers that never make sense for a chat-completion call (embedding,
  TTS, transcribe, image, audio, vision-preview, customtools, thinking,
  thought, reasoner, computer-use, computer_use).
- Allowlists known stable Gemini families (`gemini-{1.5,2.0,2.5}-{flash,pro,
  flash-lite,flash-8b}`, optionally with `-NNN`, `-exp`, `-latest`, or
  `-MM-YYYY` suffixes) so OpenAI-compatible incompatibilities (`thought_signature`,
  computer-use, customtools) cannot reach the dropdown.
- Ranks remaining models by version score → `latest` tag → date in name → id,
  so the newest stable chat model appears first.
- Appends a single env-override row (`OPENAI_MODEL`, `CLAUDE_MODEL`, etc.) at
  the end of the list when set, ensuring power users can always pick it.

## Friendly Error Mapping

`format_provider_error` translates well-known upstream errors into actionable
hints before they reach the CLI/UI surfaces:

- `thought_signature`, `computer-use` / `computer_use` → "pick a stable Gemini
  chat model".
- `reasoning_content` → "pick a non-reasoning chat model".
- Cloudflare HTML challenges → "blocked by CF on this host".
- `invalid x-api-key` / `authentication_error` → clean labelled rejection.

## Web Research Flow (UI Chat)

1. When `Web research` is enabled in Chat settings, UI fetches best-effort sources from DuckDuckGo and Wikipedia.
2. Sources are deduplicated and summarized into a compact prompt context block.
3. The context block is injected into the chat turn before provider dispatch.
4. This design is provider-agnostic and does not require MCP.
5. If web retrieval fails, chat logs/warns and proceeds without web context.

## Error Model

All errors are normalized to `LLMError`:

- `auth`
- `rate_limit`
- `bad_request`
- `network`
- `server`
- `unsupported`

`MissingCredential` extends `LLMError(kind="auth")`.

CLI maps kinds to exit codes and can emit JSON errors.
UI shows concise `st.error(...)` messages.

## CLI/UI Parity

`llm_examples.capabilities.CAPABILITIES` is the single source of truth.

- CLI parser is generated from capabilities.
- Streamlit UI renderers are keyed by capabilities.
- Parity tests assert every capability and parameter exists in both surfaces.
- Streamlit page/provider/output selections are persisted in session state across reruns.
- API `run` and chat use aligned response UX conventions (markdown rendering, long-response scrolling, and copy-friendly raw text).
- API `run` and chat both expose request progress states during provider execution.

## UI State Persistence

`llm_examples/ui/persistence.py` mirrors a small set of `st.session_state`
keys to disk so the chat experience survives Streamlit restarts and browser
reloads:

- `selected_provider`, `selected_chat_model_by_provider` — last-used provider
  and chat model per provider.
- `selected_page` — last-active page (`Chat`, `API`, or `Logs`); the default for new users is `Chat`.
- `output_mode` — last-selected `TXT`/`JSON` toggle.
- `prompt_history` — recent prompts per scope; chat scopes are
  `chat:{provider}` (per-provider, shared across all models for that
  provider), the API `run` page uses `run:{provider}`.

Storage details:

- File: `.state/llm_ui_state.json` at the repo root (gitignored).
- Format: `{"schema_version": 1, "state": {...}}`. A loader that sees a
  different `schema_version` discards the file and starts fresh, so future
  schema changes can't corrupt the UI.
- Writes are atomic: write to `.tmp`, then rename.
- Env knobs: `LLM_EXAMPLES_STATE_FILE` overrides the path;
  `LLM_EXAMPLES_DISABLE_STATE=1` turns persistence into a no-op (used by the
  test suite via `conftest.py`).

The hook lives entirely inside `state.py`: `_ensure_loaded()` rehydrates the
session once per browser session, every mutator (`set_selected_provider`,
`set_selected_page`, `set_output_mode`, `set_selected_chat_model`,
`add_prompt_history`, `clear_prompt_history`) calls `_persist()` after
mutating session state.

## UI Port Resilience

`make run` / `make ui` invokes `scripts/find_free_port.py` before starting
Streamlit. The helper opens a `SO_REUSEADDR` socket against `127.0.0.1:PORT`
(span configurable via `PORT_SPAN`, default 50) and prints the first port that
binds successfully. The Makefile then passes that port to `streamlit
--server.port`, so a busy default no longer crashes the UI; the chosen port is
logged when it differs from the requested one.

## Documentation Parity

Behavior changes are not complete until docs are synchronized in the same commit.

- `README.md`
- `CLAUDE.md` / `AGENTS.md`
- `docs/USAGE.md`
- `INSTALL.md`
- `CREATE-PR.md`
