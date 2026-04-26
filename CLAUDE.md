# Agent Conventions

This repo is agent-first. Keep behavior, docs, and tests synchronized.

## Required Sync Rule

Any behavioral code change must update all relevant files in the same commit:

- `README.md`
- `docs/PLAN.md`
- `CLAUDE.md` (and `AGENTS.md`, which must remain a symlink)
- Any impacted ADR or usage doc

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

## Provider Rule

- Every provider module implements full `BaseClient` methods:
  - `list_models`
  - `chat`
  - `stream`
  - `check`
- Provider-specific normalization belongs in provider modules.
- Include one standalone script in `examples/` per provider.

## Testing Rule

- Unit tests cannot use real network.
- Use `@pytest.mark.parametrize` for provider matrix tests.
- Keep coverage gate at 100%.
- Any code or behavior change must be validated before handoff using relevant `make` targets.
- For surface changes, verify both paths: at least one CLI command (`make providers` or `make run-cli ...`) and UI startup (`make run`).

## Build Rule

`make check` is the CI gate and must include:

- lint
- lint-imports
- type (`mypy --strict`)
- test
- score (`scripts/score_architecture.py --min-score 8`)
