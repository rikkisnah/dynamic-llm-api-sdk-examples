# Implementation Plan — dynamic LLM API SDK examples

> **Status:** Locked for implementation (Task 1 deliverable from `INSTRUCTIONS-build-it.md`).
> **Audience:** Future agent sessions (Claude Code / Codex CLI) and human reviewers.
> **Update rule:** Any code change that diverges from this plan must update this file in the same commit, alongside `README.md` and `CLAUDE.md`/`AGENTS.md`.
> **Provenance:** Locked after the user resolved every ambiguity in §17 — see that section before treating any item here as "the agent decided."

---

## 1. Goals

Demonstrate **multi-provider LLM SDK usage** across six vendors, exposed through two surfaces at strict feature parity:

- **CLI** (Python 3, managed with `uv`)
- **UI** (Streamlit)

Providers in scope: **OpenAI, Claude (Anthropic), Gemini (Google), DeepSeek, Qwen (DashScope), Z.ai**.

Architecture quality bar: emulate the eight dimensions of `/mnt/data/src/scm/stc/scripts/score_architecture.py`, **plus four agent-first dimensions** (§13). All twelve gated ≥ 8/10 in CI.

Two layers of "example" exist in this repo:

- **`llm_examples/providers/<vendor>_provider.py`** — production-shaped adapter wired into the CLI/UI. Reads as a clean, vendor-isolated reference for that SDK *within* the package abstraction (depends on `domain_types`, `BaseClient`).
- **`examples/<vendor>.py`** — fully **standalone** runnable scripts with **zero package imports**. These are the "copy one file and learn one SDK" surface. Each script is self-contained: read key from env, list models, run a prompt, print result.

Together those satisfy both the spec ("examples") and the scorecard (tiered, testable architecture).

## 2. Non‑negotiables (from spec)

| Constraint | Detail |
|------------|--------|
| CLI runtime | Python 3, dependency/tooling via **`uv`** |
| Build / tasks | A **`Makefile`** documents common commands |
| UI | **Streamlit** |
| Agent docs | `AGENTS.md` symlinked to `CLAUDE.md` |
| Doc/code sync | Every code change keeps `README.md` + `CLAUDE.md`/`AGENTS.md` + this `PLAN.md` current |
| Architecture | 100 % pass on the architecture scorecard (12 dimensions, ≥ 8 each) |

## 3. Architecture (tiered)

Tier rule: a module may import from **lower or equal** tiers only. Upward imports are a CI failure.

| Tier | Module | Responsibility |
|------|--------|----------------|
| 0 | `domain_types.py` | TypedDicts/dataclasses for the LLM call surface: `ProviderName`, `ModelInfo`, `ChatRequest`, `ChatResponse`, `Usage`, `ProviderConfig`, `LLMError`, `MissingCredential` (subclass of `LLMError`, `kind="auth"`) |
| 0 | `config.py` | Load `.env` (via `python-dotenv`); resolve per-provider key + base URL; raise `MissingCredential` |
| 0 | `capabilities.py` | Single source of truth (`CAPABILITIES` registry) of operations × parameters; defines `Parameter` and `Capability` dataclasses; consumed by both `cli.parser` and `ui.app` (see §8 parity contract). Capability/Parameter live here — not in `domain_types` — to keep call-surface types separate from UX schema. |
| 1 | `llm_client.py` | `BaseClient` ABC: `list_models()`, `chat(req)`, `stream(req)`, `check()` |
| 2 | `providers/openai_provider.py` | OpenAI native SDK (`openai`) adapter |
| 2 | `providers/claude_provider.py` | Anthropic native SDK (`anthropic`) adapter |
| 2 | `providers/gemini_provider.py` | Google native SDK (`google-genai`) adapter |
| 2 | `providers/qwen_provider.py` | Qwen native SDK (`dashscope`) adapter |
| 2 | `providers/deepseek_provider.py` | DeepSeek adapter — uses the **OpenAI-compatible SDK** path (`openai` SDK pointed at `api.deepseek.com`), per DeepSeek's own docs. Kept as its own module so it reads as "calling DeepSeek," not "repurposing OpenAI." |
| 2 | `providers/zai_provider.py` | Z.ai native SDK (`zai-sdk`) adapter; falls back to direct httpx against the documented OpenAI-compatible endpoint if the SDK is unstable (decision recorded in ADR 0001) |
| 3 | `registry.py` | `PROVIDERS` tuple + `get_client(provider)` dispatch table |
| 4 | `services.py` | `list_models`, `run_prompt`, `stream_prompt`, `check_connection`; adds latency timing + error normalization |
| 5 | `cli/parser.py` | Builds the argparse tree **from `capabilities.CAPABILITIES`** (no hand-coded duplicate of options) |
| 5 | `cli/commands.py` | Dispatch dict mapping command → handler |
| 5 | `cli/cmd_list.py`, `cmd_run.py`, `cmd_check.py`, `cmd_providers.py` | Per-command handlers |
| 5 | `ui/app.py` | Streamlit entry; renders widgets **from `capabilities.CAPABILITIES`** |
| 5 | `ui/state.py` | Session-state helpers |
| 5 | `ui/helpers.py` | Formatting, JSON pretty-print |

`__init__.py` files contain **only re-exports** (per the modularity rule). Every module's docstring opens with a `Tier N:` marker (per the documentation rule).

## 4. Repo Layout

```
dynamic-llm-api-sdk-examples/
├── pyproject.toml            # uv-managed; entry point: llm-examples
├── uv.lock
├── Makefile
├── README.md                 # quickstart, env-var table, parity matrix
├── CLAUDE.md                 # conventions (tier rule, parity contract, …)
├── AGENTS.md -> CLAUDE.md    # symlink
├── .env.example              # all six provider keys, commented
├── .gitignore                # .env, __pycache__, .venv, .coverage, …
├── docs/
│   ├── PLAN.md               # this file
│   ├── INSTALL.md
│   ├── USAGE.md              # CLI ↔ UI parity recipes
│   ├── HOW-IT-WORKS.md       # tier diagram, request lifecycle
│   └── adr/
│       ├── 0001-provider-abstraction.md
│       ├── 0002-cli-ui-parity-contract.md
│       ├── 0003-error-model.md
│       ├── 0004-agent-first-scorecard.md
│       └── 0005-standalone-examples-vs-package.md
├── examples/                 # standalone single-file scripts (no package import)
│   ├── README.md             # how to run any example
│   ├── openai_example.py
│   ├── claude_example.py
│   ├── gemini_example.py
│   ├── deepseek_example.py
│   ├── qwen_example.py
│   └── zai_example.py
├── llm_examples/             # main package
│   ├── __init__.py
│   ├── domain_types.py
│   ├── config.py
│   ├── capabilities.py
│   ├── llm_client.py
│   ├── providers/…
│   ├── registry.py
│   ├── services.py
│   ├── cli/…
│   └── ui/…
├── scripts/
│   └── score_architecture.py # adapted scorecard for this package (12 dims)
└── tests/
    ├── conftest.py
    ├── helpers.py            # fake transports, fixtures
    ├── test_smoke.py
    ├── test_registry.py
    ├── test_services.py
    ├── test_providers.py     # parametrized per provider, mocked HTTP
    ├── test_cli.py
    ├── test_capabilities.py  # parity registry consistency
    ├── test_parity.py        # CLI ↔ UI symmetry check (option-level)
    ├── test_examples.py      # examples/*.py import & dry-run with mocks
    └── test_score.py         # gates architecture score in CI
```

## 5. Data Flow

```
UI(Streamlit) ──┐
                ├─► services.run_prompt(provider, model, prompt)
CLI(cmd_run) ──┘        │
                        ▼
              registry.get_client(provider)
                        │
                        ▼
          providers.<vendor>.chat(req) ──► HTTP
                        │
              ChatResponse{text, model, latency_ms, usage?, raw_id?}
```

**Parity contract:** UI and CLI **only** call `llm_examples.services`. Neither imports a provider module directly. Per-vendor quirks (no `usage`, no list-models, etc.) are normalized inside the provider module — never above it.

## 6. Provider Strategy

Native SDK per vendor, except DeepSeek which uses its documented OpenAI-compatible path:

| Provider | Library | Endpoint | Default model |
|---|---|---|---|
| OpenAI | `openai` | default | `gpt-4o-mini` |
| Claude | `anthropic` | default | `claude-haiku-4-5` |
| Gemini | `google-genai` (the new unified SDK, **not** `google-generativeai`) | default | `gemini-2.5-flash` |
| DeepSeek | `openai` SDK with `base_url=https://api.deepseek.com` (DeepSeek-recommended path) | DeepSeek | `deepseek-chat` |
| Qwen | `dashscope` | DashScope-International | `qwen-plus` |
| Z.ai | `zai-sdk` (fallback: `httpx` against `https://api.z.ai/api/paas/v4`) | Z.ai | `glm-4.6` |

Each `providers/*.py` doubles as a per-vendor reference. The "copy one file and run it" surface lives in `examples/` (§4) — those are deliberately untethered from the package.

If a provider's `list_models` is unsupported or unhelpful, the provider module ships a **documented fallback allowlist** of model IDs (per spec §3 fallback clause). README documents which providers fall back.

## 7. Env Vars

All vars optional in `.env.example` — only required at the moment a provider is invoked.

| Provider | Key var | Optional override |
|----------|---------|-------------------|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` |
| Claude | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL` |
| Gemini | `GEMINI_API_KEY` | — |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL` |
| Qwen | `DASHSCOPE_API_KEY` | `DASHSCOPE_BASE_URL` |
| Z.ai | `ZAI_API_KEY` | `ZAI_BASE_URL` |

Default models live in `llm_examples/providers/<vendor>_provider.py` as a `DEFAULT_MODEL` constant and are overridable from CLI (`--model`) and UI (model selector).

## 8. CLI ↔ UI Parity — single registry, two renderers

Hand-maintaining two parallel surfaces is how parity rots. Instead, both surfaces render from one declarative source.

**`llm_examples/capabilities.py`** defines:

```python
@dataclass(frozen=True)
class Parameter:
    name: str
    type: Literal["str", "int", "bool", "path", "enum:provider", "enum:model"]
    required: bool = False
    default: Any = None
    help: str = ""

@dataclass(frozen=True)
class Capability:
    name: str                       # e.g. "run"
    summary: str                    # one-liner
    params: tuple[Parameter, ...]
    json_output: bool = True        # every command supports --json by default; set False only if the command has no structured payload to emit
    streams: bool = False           # implies a UI stream renderer too

CAPABILITIES: tuple[Capability, ...] = (
    Capability("providers", "List configured providers", ()),
    Capability("list-models", "List models for a provider",
        (Parameter("provider", "enum:provider", required=True),)),
    Capability("run", "Run a one-shot prompt",
        (
            Parameter("provider", "enum:provider", required=True),
            Parameter("model", "enum:model"),
            Parameter("prompt", "str"),
            Parameter("prompt-file", "path"),
            Parameter("system", "str"),
            Parameter("max-tokens", "int", default=512),
            Parameter("stream", "bool", default=False),
        ),
        streams=True),
    Capability("check", "Validate credentials for a provider",
        (Parameter("provider", "enum:provider", required=True),)),
)
```

- `cli/parser.py` walks `CAPABILITIES` to build subcommands and flags.
- `ui/app.py` walks `CAPABILITIES` to render widgets (selectbox, textarea, number_input, checkbox).
- `tests/test_capabilities.py` asserts internal consistency (no dup names, every param has help, every `streams=True` capability has a stream renderer wired).
- `tests/test_parity.py` asserts every `Capability.name` is reachable from both `cli.parser` and `ui.app` and that **every parameter** is honored by both — option-level, not just command-name level.

Resulting parity matrix (rendered, not hand-edited). `--json` is supported on **every** command (it's a global flag, not a per-capability option), so it's omitted from the per-row parameter list:

| Capability | Parameters | CLI | UI |
|---|---|---|---|
| `providers` | — | command | sidebar |
| `list-models` | `provider` | command | button |
| `run` | `provider`, `model`, `prompt`/`prompt-file`, `system`, `max-tokens`, `stream` | command | form |
| `check` | `provider` | command | button |

CLI also accepts `--prompt-file -` (stdin) — modeled as the `path` parameter type's documented sentinel.

## 9. Error Handling

Single normalized exception:

```python
class LLMError(Exception):
    provider: ProviderName
    model: str | None
    kind: Literal["auth", "rate_limit", "bad_request", "network", "server", "unsupported"]
    cause: Exception | None
    message: str
```

- `MissingCredential` (raised by `config.py` when a required env var is absent) is a **subclass of `LLMError` with `kind="auth"`**, so the single normalized error path holds end-to-end — services and surfaces never need a separate handler for missing keys.
- Provider modules translate vendor exceptions → `LLMError`.
- `services` adds latency + re-raises.
- **CLI:** prints concise message; exit code per `kind` (2=auth, 3=rate_limit, 4=bad_request, 5=network, 6=server, 7=unsupported); `--json` emits `{"ok": false, "error": {...}}`.
- **UI:** `st.error(message)` — never a stack trace.
- API keys **never** appear in error messages or logs (enforced by dimension 12 secret-hygiene scan).

## 10. Streaming & Connection Check (in MVP, by user direction)

Both are MVP scope by explicit user decision (see §17 Q2). Risk: extra surface across six SDKs. Mitigation:

- **Streaming:** `BaseClient.stream(req) -> Iterable[str]` yields text deltas. Each provider implements via its native streaming primitive. CLI prints deltas to stdout flushed; UI uses `st.write_stream`. Providers that lack native streaming may simulate by chunking a non-streamed response — and that simulation must be loud (logged + flagged in `--json` output) so it's never silent.
- **Connection check:** `BaseClient.check() -> CheckResult{ok, latency_ms, detail}` does the cheapest call that validates credentials (typically `list_models` with a short timeout, or a 1-token completion if the vendor has no list endpoint).

## 11. Build / Tasks (Makefile)

```
make install        # uv sync
make install-dev    # uv sync --group dev
make ui             # uv run streamlit run llm_examples/ui/app.py
make run P=openai PROMPT="hi"
make list P=openai
make check-conn P=openai
make example V=openai           # runs examples/openai_example.py
make test           # pytest --cov, COV_FAIL_UNDER=100
make test-%         # single test file: make test-providers
make lint           # ruff check
make lint-imports   # import-linter (enforces tier rule)
make type           # mypy --strict llm_examples/
make fmt            # ruff format
make score          # python scripts/score_architecture.py --min-score 8
make check: lint type test score    # CI gate — type and score are mandatory
make all: check                     # alias kept for muscle memory
```

`type` and `score` are both in `check`, not just `all`, so the strict-mypy and architecture gates are exactly what CI runs. Dimension 6 of the scorecard depends on this.

## 12. Testing Strategy

- `pytest` + `pytest-cov` with `COV_FAIL_UNDER = 100`.
- HTTP mocked via `respx` (httpx) and SDK monkeypatching where SDKs bypass httpx.
- **Zero real network in unit tests** (gated by dimension 12; pytest fixture aborts on real socket).
- Heavy `@pytest.mark.parametrize` use (per scorecard test-quality rule); one parametrize row per provider for: chat success, auth error, rate-limit error, list-models success, list-models fallback, stream success, check success.
- `tests/test_smoke.py` ensures `import llm_examples` works.
- `tests/test_capabilities.py` asserts the registry is internally consistent.
- `tests/test_parity.py` asserts CLI + UI both honor every `Capability` *and* every `Parameter` from `CAPABILITIES` (option-level parity, per Codex review).
- `tests/test_examples.py` imports each `examples/*.py` and runs its `main()` with mocked transport, proving the standalone scripts execute.
- `tests/test_score.py` runs the scorecard and asserts every dimension ≥ 8.

## 13. Architecture Scorecard — 12 dimensions

The first 8 mirror `score_architecture.py`. Dimensions 9–12 are added because this repo is **agent-first**: future Claude/Codex sessions must be able to extend it confidently without ambient knowledge.

| # | Dimension | What it checks |
|---|---|---|
| 1 | **Readability** | Files ≤ 800 LOC, functions ≤ 100 LOC & nesting ≤ 5, every module has a docstring |
| 2 | **Modularity** | Tier rule (no upward imports); `__init__.py` is re-exports only; package importable |
| 3 | **Scalability** | ≥ 6 provider modules; CLI dispatch table present; `CAPABILITIES` registry present |
| 4 | **Test Quality** | `COV_FAIL_UNDER=100`; `helpers.py`, `conftest.py`, `test_smoke.py` present; parametrize-heavy; no for-loop test patterns |
| 5 | **Documentation** | ≥ 5 ADRs; every module has `Tier N:` marker in header docstring; `README.md` + `docs/INSTALL.md` + `docs/USAGE.md` + `docs/HOW-IT-WORKS.md` + `docs/PLAN.md` exist |
| 6 | **Build & Packaging** | `mypy --strict` covers full package and is wired into `make check`; Makefile has `lint-imports`, `check: lint type test score`, `test-%` rule; `import llm_examples` succeeds |
| 7 | **Type Safety** | `domain_types.py` exists and is widely imported; zero `dict[str, Any]` in public signatures |
| 8 | **Code Duplication** | No duplicate function names across `providers/`; `services.py` exists and is ≤ 200 LOC; provider-specific normalization stays inside provider modules |
| 9 | **Agent Discoverability** | `AGENTS.md` is a symlink to `CLAUDE.md`; both reference the tier map; `README.md` has a machine-parseable Commands & Env-Vars table; `docs/PLAN.md` exists and mentions every provider in §6 |
| 10 | **Provider Symmetry** | Every provider class implements the full `BaseClient` ABC (no `NotImplementedError` leaks); each provider has a parametrized test row for every operation; an `examples/<vendor>.py` exists for every provider in §6 |
| 11 | **CLI ↔ UI Parity** | Both surfaces consume `capabilities.CAPABILITIES`; `tests/test_parity.py` asserts every operation **and every parameter** is reachable from both — drift fails CI |
| 12 | **Secret Hygiene & Reproducibility** | `.env` gitignored; `.env.example` lists every key the code reads; no API-key string literals in source (regex scan); `uv.lock` committed; unit tests run with network disabled |

Each dimension scored 0–10. CI gate (via `make check`): every dimension ≥ 8.

## 14. Documentation Plan (kept in lockstep with code)

- `README.md` — overview, quickstart, env-var table, parity matrix, links to `docs/` and `examples/`.
- `docs/INSTALL.md` — `uv` setup, `.env` setup, smoke test.
- `docs/USAGE.md` — CLI recipes + UI walkthrough; one section per provider.
- `docs/HOW-IT-WORKS.md` — tier diagram, request lifecycle, error model.
- `docs/PLAN.md` — this file.
- `docs/adr/0001-provider-abstraction.md` — why per-vendor modules over unified layer; Z.ai SDK choice.
- `docs/adr/0002-cli-ui-parity-contract.md` — `CAPABILITIES` registry as single source of truth.
- `docs/adr/0003-error-model.md` — `LLMError` kinds and exit codes.
- `docs/adr/0004-agent-first-scorecard.md` — rationale for dimensions 9–12.
- `docs/adr/0005-standalone-examples-vs-package.md` — why `examples/` is decoupled from the package.
- `examples/README.md` — how to run any single-file example.
- `CLAUDE.md` / `AGENTS.md` — conventions: tier rule, services-only access from cli/ui, parametrize tests, doc-sync rule, no-real-network rule, capability-registry rule.

## 15. Work Sequence (post-approval)

1. **Bootstrap.** `uv init`, `pyproject.toml`, `Makefile`, `.env.example`, `.gitignore`, `AGENTS.md → CLAUDE.md` symlink, empty package skeleton, `tests/test_smoke.py` → green.
2. **Tier 0–1.** `domain_types`, `config`, `capabilities`, `llm_client` ABC + tests.
3. **Tier 2 (one provider at a time, each with parametrized tests + a matching `examples/<vendor>.py`):** OpenAI → DeepSeek → Z.ai → Qwen → Claude → Gemini.
4. **Tier 3–4.** `registry`, `services` + tests.
5. **Tier 5a — CLI.** `parser` (built from `CAPABILITIES`), `commands` (dispatch dict), per-command handlers, `--json` mode, streaming output.
6. **Tier 5b — UI.** Streamlit `app.py` (built from `CAPABILITIES`), sidebar, model picker, prompt area, streaming via `st.write_stream`. Manually verified in browser per spec.
7. **Parity wiring.** `tests/test_capabilities.py` and `tests/test_parity.py` go green.
8. **Live verification.** Smoke each of the six providers with the user's keys; mark each "verified live" in README.
9. **Docs + ADRs + scorecard.** `scripts/score_architecture.py` adapted for 12 dimensions; iterate until all ≥ 8.

## 16. Open Items

- **Z.ai SDK stability.** If `zai-sdk` is unstable in practice, switch to `httpx` against `https://api.z.ai/api/paas/v4`. Decision recorded in ADR 0001 once we've tried both.
- **Default model drift.** Vendor model names change frequently. Defaults in `providers/<vendor>_provider.py` are intentionally the cheapest current option and will be revisited each minor release.
- **Streaming simulation policy.** If any provider can't truly stream, the simulation must be visibly flagged (per §10). If user later prefers "no fake stream — just disable `--stream` for that provider," we adjust §10 and re-score dimension 11.

## 17. Decision Trail (resolved ambiguities)

Resolved with the user during plan negotiation on 2026-04-25, **before** this file was committed. Each row pairs the question I asked with the user's verbatim reply, so future reviewers (or independent agents that don't share this conversation context) can audit that no decision was fabricated. Do not re-litigate without a fresh user signal.

| # | Question (asked by agent) | User's verbatim reply | Resolution |
|---|---|---|---|
| Q1 | Native per-vendor SDKs, or unified library (LiteLLM)? | *"no keep it separe as it is meant also to be used as examples using the respective LLM providers"* | Native per-vendor; each provider module reads as a standalone "how to call this vendor" reference. |
| Q2 | Streaming + connection-check in MVP, or deferred? | *"Yes include"* | Both in MVP. Risk of extra surface across six SDKs accepted; mitigation in §10. |
| Q3 | Plan as `docs/PLAN.md` or chat-only? | *"yes add it in PLAN.md"* | Commit as `docs/PLAN.md`; persists across sessions; doubles as agent memory. |
| Q4 | `--json` output mode from day one? | *"yes"* | Yes — supported on every command (see §8 matrix note). |
| Q5 | Provider key availability for live verification? | *"and yes i ahve working keys"* | All six keys available. Live verification is part of acceptance (§15 step 8), in addition to mocked-HTTP unit tests. |
| Q6 | Pick default models, or wait for user picks? | *"default models that is fine we can change later. it should be changeable"* | Agent picks reasonable defaults (§6); all overridable via CLI `--model` / UI selector. |
| Q5b | Architecture dimensions — keep 8, or add agent-first? | *"I need to add all dimensions, i need you to add more if you thin is needed as this repo is agentic first class citizen"* | Add 4 agent-first dimensions (Discoverability, Provider Symmetry, CLI/UI Parity, Secret Hygiene & Reproducibility) for 12 total, all CI-gated ≥ 8. |

**Audit instruction for independent reviewers:** if the verbatim quotes above don't match the actual conversation transcript, treat the corresponding rows as *open* — not decided — and revert §1, §6, §8, §10, §13, §15 accordingly. The plan's authority on these points rests entirely on those quotes being faithful.

Codex review pass 1 (2026-04-25) flagged six findings; resolutions:

| Codex finding | Action |
|---|---|
| #1 Locked before ambiguities resolved | **N/A** — plan was locked *after* §17 Q&A; this provenance section makes that explicit. |
| #2 Streaming/check elevated to MVP | **Accepted as user-directed scope** (§17 Q2, §10 risk note). |
| #3 DeepSeek wording contradiction (§3 vs §6) | **Fixed** — §3 row now says "OpenAI-compatible SDK path"; §6 echoes the same. |
| #4 "Copy one file" claim was false | **Fixed** — added `examples/` directory of standalone single-file scripts (§1, §4); ADR 0005 records the split. |
| #5 Parity test only matched command names | **Fixed** — `capabilities.CAPABILITIES` is now the single source for both surfaces; `tests/test_parity.py` asserts option-level symmetry (§8, dim 11). |
| #6 CI gate didn't include `score` | **Fixed** — `make check: lint type test score` (§11). |

Codex review pass 2 (2026-04-25) flagged five findings on the revised plan; resolutions:

| Codex finding | Action |
|---|---|
| #1 Unverified provenance in §17 | **Fixed** — §17 now quotes the user's verbatim replies and includes an explicit audit instruction so reviewers without conversation context can verify the trail. |
| #2 `make check` didn't run `mypy` | **Fixed** — gate is now `make check: lint type test score` (§11); dimension 6 (§13) updated to match. |
| #3 `Capability` assigned to two modules | **Fixed** — `Capability`/`Parameter` live in `capabilities.py` only (§3); `domain_types.py` row no longer lists it and now also lists `MissingCredential` for completeness. |
| #4 `--json` policy was inconsistent | **Fixed** — `--json` is a **global flag** on every command, not a per-capability option; §8 matrix and dataclass comment clarified. |
| #5 `MissingCredential` outside the unified error path | **Fixed** — `MissingCredential` is now defined as a subclass of `LLMError` with `kind="auth"` (§3 row, §9). |
