# Agent Conventions

This repo is agent-first. Keep behavior, docs, and tests synchronized.

## Required Sync Rule

**Every code change is incomplete until all three gates pass in the same commit.** No
exceptions, no follow-up commits, no "I'll fix the docs later." If any of the
three is unchanged when the change requires it, the change is unfinished:

1. **Code + tests + 100% coverage.** Add or update tests for the new behavior.
   `make check` must pass: ruff lint, import-linter, `mypy --strict`, the full
   test suite at `--cov-fail-under=100`, and the architecture score gate
   (`--min-score 8` across all 12 dimensions). Do not lower the coverage gate
   or the score-gate threshold to make a change land.
2. **Documentation sync.** Update every doc that mentions the changed
   behaviour, in the same commit:
   - `README.md`
   - `CLAUDE.md` (and `AGENTS.md`, which must remain a symlink)
   - `docs/USAGE.md`, `docs/HOW-IT-WORKS.md`
   - `INSTALL.md`, `CREATE-PR.md` when the workflow changes
   - `.env.example` when env vars change
   - relevant ADRs under `docs/adr/`
3. **Live validation when applicable.** If the change touches provider behaviour
   or live API paths, run `make test-llm-all` before declaring it done.

Pre-commit checklist (run mentally before claiming "done"):

- [ ] Behaviour change is reflected in tests, and `make check` passes locally.
- [ ] Coverage is still 100% on non-omitted modules (no new uncovered branches).
- [ ] All affected docs above were updated in this same change set.
- [ ] If a Make target / env var / capability was added or renamed, both
      `make help` and the relevant doc tables show it.
- [ ] If a UI-visible behaviour changed (page order, defaults, persistence
      shape, friendly errors), the README/USAGE/HOW-IT-WORKS lines reflect it.

## Architecture Rule (Tiered)

Each module starts with `Tier N:` in the module docstring.

Allowed imports are lower/equal tier only:

1. Tier 0: `domain_types.py`, `config.py`, `capabilities.py`
2. Tier 1: `llm_client.py`
3. Tier 2: `providers/*`
4. Tier 3: `registry.py`
5. Tier 4: `services.py`
6. Tier 5: `cli/*`, `ui/*`

## Parity Rule

CLI and UI must both consume `llm_examples.capabilities.CAPABILITIES`.

- No one-off capability wired in only one surface.
- Add/update tests in `tests/test_capabilities.py` and `tests/test_parity.py`.
- Keep `--provider` optional on CLI: when omitted, both CLI and UI resolve the default provider from `AI_PROVIDER` / `DEFAULT_AI_PROVIDER` (case-insensitive aliases supported, e.g. `anthropic`/`claude`, `codex`/`oca`).
- Keep `.env` loading dual-pathed: repo-root `.env` plus `llm_examples/.env`. Process env always wins; root `.env` overrides `llm_examples/.env`.
- Keep output-mode parity for user calls: both CLI/Make and UI must support readable text and JSON render modes.
- UI may add non-capability page navigation (e.g., chat/logs pages) as long as capability parity remains unchanged.
- For UI prompt-entry surfaces (`run` and chat), preserve recent-prompt memory with explicit choose/clear controls.
- Saved prompts in chat are scoped per provider (one shared list for all models of that provider). The picker + send/clear controls render above the composer whenever there is at least one saved prompt for the active provider; the API `run` page keeps its own `run:{provider}` scope.
- Persist UI state across reloads to `.state/llm_ui_state.json` (gitignored, schema-versioned): selected provider, selected chat model per provider, selected page, output mode, and prompt history. Honour `LLM_EXAMPLES_STATE_FILE` (path override) and `LLM_EXAMPLES_DISABLE_STATE=1` (no-op) env knobs.
- Keep chat UI conversation-first: keep history/composer primary and place advanced controls under collapsible settings.
- Keep chat attachments in-composer (`+` on message box) for file/image flows, including paste support where Streamlit/browser provides it.
- Keep chat web-research optional and provider-agnostic: inject summarized web sources in the prompt for all providers without breaking normal chat when web lookup fails.
- Keep assistant response UX readable and actionable: preserve markdown formatting, keep long replies scrollable, and expose copy-friendly raw text.
- Keep API response UX aligned with chat for readability and copyability, with visible copy-ready text blocks in TXT mode.
- Keep API `run` progress visibility aligned with chat (`calling`, `streaming/generating`, `completed` with elapsed time).
- Keep quote banner UX stable: top quote remains visible with a refresh action and refresh must preserve current page context.
- Keep version discoverability on both surfaces (`llm-examples --version` and visible UI version label).

## Provider Rule

- Every provider module implements full `BaseClient` methods:
  - `list_models`
  - `chat`
  - `stream`
  - `check`
- Provider-specific normalization belongs in provider modules.
- Shared retry/empty-token-limit/chat-model-filter/friendly-error helpers live in `providers/_common.py` and are reused by all adapters.
- Keep provider hardening for empty token-limit replies (e.g., reasoning-heavy models) inside provider adapters, with clear actionable errors after retries. The shared retry floor is `RETRY_MIN_MAX_TOKENS=512` clamped to `RETRY_MAX_MAX_TOKENS=4096`.
- Keep Z.ai continuation hardening in provider adapters: when non-empty output hits token-limit finish, auto-continue and append seamlessly.
- Keep multimodal image forwarding implemented in provider adapters (OpenAI/Claude/Gemini/DeepSeek/Qwen/Z.ai/OCA), with clear errors when selected models do not support vision.
- Gemini routes through Google's OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai`); the chat-model filter allowlists stable Gemini families to avoid `thought_signature`, computer-use, customtools, and thinking variants over the OpenAI-compatible protocol.
- The Codex / OCA provider authenticates via `OCA_API_KEY` / `OCA_ACCESS_TOKEN` (with `~/.codex/auth.json` as a fallback), uses the documented LiteLLM proxy base URL by default, sends `OCA_CLIENT_HEADER`/`OCA_CLIENT_VERSION` headers, and applies `REASONING_EFFORT` (default `xhigh`).
- Include one standalone script in `examples/` per provider (including OCA).

## Testing Rule

- Unit tests cannot use real network.
- Use `@pytest.mark.parametrize` for provider matrix tests.
- Keep coverage gate at 100%.
- Any code or behavior change must be validated before handoff using relevant `make` targets.
- For surface changes, verify both paths: at least one CLI command (`make providers` or `make run-cli ...`) and UI startup (`make run`).
- For quote/banner changes, verify refresh behavior from both `Chat` and `Logs` pages and keep page context stable (no redirect to `API`).
- For provider/parsing changes, validate every path: `make check`, plus `make test-llm-all` with the deterministic hello prompt flow.

## UI Rule

- `make run` / `make ui` must remain port-resilient: probe the requested
  `PORT` via `scripts/find_free_port.py` and fall back to the next free port in
  `[PORT, PORT + PORT_SPAN)` (default span: 50) before invoking Streamlit.
- Streamlit widgets that share a `key=` with a persisted `st.session_state`
  entry (e.g. `selected_page`) must NOT also pass `index=`/`value=` — Streamlit
  warns "default value + session_state" when both are used. Initialize
  `st.session_state[key]` via the appropriate getter (e.g.
  `get_selected_page(DEFAULT_PAGE)`) before the widget renders, then attach
  `on_change=persist_session_state` so user-driven mutations land on disk.

## Makefile Rule

- Every `.PHONY` target must carry an inline `## description` annotation so it
  appears in `make help`. The `tests/test_makefile.py` regression test enforces
  this — adding a target without an annotation fails the test suite.
- Group targets with `##@ Section` headers so `make help` renders them under a
  bold section title. Order in the file equals order in help output.
- The `help` target is auto-generated by awk from `## description` and `##@`
  markers — do **not** hand-edit a duplicate help block. Add new targets with
  annotations and they appear automatically.
- Use `VAR=value` style for invocation parameters (e.g.
  `make run-cli P=openai PROMPT='hello' OUT=json`). Document the variables
  inside the target's `## description` and in the static `Variables` footer of
  the `help` recipe so users can discover them at a glance.
- The pattern rule `test-%` is annotated with a representative example
  (`make test-providers` → `tests/test_providers.py`).

## Build Rule

`make check` is the CI gate and must include:

- lint
- lint-imports
- type (`mypy --strict`)
- test
- score (`scripts/score_architecture.py --min-score 8`)
