# Agent Conventions

This repo is agent-first. Keep behavior, docs, and tests synchronized.

## Required Sync Rule

Any behavioral code change must update all relevant files in the same commit:

- `README.md`
- `CLAUDE.md` (and `AGENTS.md`, which must remain a symlink)
- Any impacted ADR or usage doc (at minimum `docs/USAGE.md` and `docs/HOW-IT-WORKS.md`)
- Keep root prompt docs current when workflow changes: `INSTALL.md`, `CREATE-PR.md`.

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
- Keep output-mode parity for user calls: both CLI/Make and UI must support readable text and JSON render modes.
- UI may add non-capability page navigation (e.g., chat/logs pages) as long as capability parity remains unchanged.
- For UI prompt-entry surfaces (`run` and chat), preserve recent-prompt memory with explicit choose/clear controls.
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
- Keep provider hardening for empty token-limit replies (e.g., reasoning-heavy models) inside provider adapters, with clear actionable errors after retries.
- Keep Z.ai continuation hardening in provider adapters: when non-empty output hits token-limit finish, auto-continue and append seamlessly.
- Keep multimodal image forwarding implemented in provider adapters (OpenAI/Claude/Gemini/DeepSeek/Qwen/Z.ai), with clear errors when selected models do not support vision.
- Include one standalone script in `examples/` per provider.

## Testing Rule

- Unit tests cannot use real network.
- Use `@pytest.mark.parametrize` for provider matrix tests.
- Keep coverage gate at 100%.
- Any code or behavior change must be validated before handoff using relevant `make` targets.
- For surface changes, verify both paths: at least one CLI command (`make providers` or `make run-cli ...`) and UI startup (`make run`).
- For quote/banner changes, verify refresh behavior from both `Chat` and `Logs` pages and keep page context stable (no redirect to `API`).
- For provider/parsing changes, validate every path: `make check`, plus `make test-llm-all` with the deterministic hello prompt flow.

## Build Rule

`make check` is the CI gate and must include:

- lint
- lint-imports
- type (`mypy --strict`)
- test
- score (`scripts/score_architecture.py --min-score 8`)
