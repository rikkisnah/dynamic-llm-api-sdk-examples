# Build: dynamic LLM API SDK examples

## Goal

Build a small application that demonstrates “hello world”–style SDK usage (e.g. list models, run a prompt) against **multiple** LLM providers, with two surfaces:

- **UI** (Streamlit)
- **CLI** (Python 3, managed with `uv`)

Quality bar: clean, maintainable, and documented. **UI and CLI must be feature‑parity** (anything doable in the UI should be doable from the CLI).

---

## Non‑negotiables (stack & repo)

| Constraint | Detail |
|------------|--------|
| CLI runtime | Python 3, dependency/tooling via **`uv`** |
| Build / tasks | A **`Makefile`** is present and documents common commands |
| UI | **Streamlit** |
| Agent docs | `AGENTS.md` is **symlinked** to `CLAUDE.md` (both Claude- and Codex-style agents may follow the same file) |
| Code quality & docs | Follow conventions in `AGENTS.md` / `CLAUDE.md`. **Any** code change should keep those files and **`README.md`** in sync with behavior. |
| Architecture / review | Aim for a **100%** pass on architecture scoring, using the **same ideas** as `/mnt/data/src/scm/stc/scripts/score_architecture.py` (treat that script as the conceptual bar, not necessarily as a direct dependency). |

---

## Product requirements

### 1) Dynamic, multi-provider LLM access

- The app must be able to **select and call different LLM providers at runtime** (not hard‑coded to a single backend).
- Support these **APIs / providers** (user will supply keys in `.env`):

  - Qwen  
  - Gemini  
  - DeepSeek  
  - Claude  
  - OpenAI  
  - Z.ai  

- Exact env var names and client libraries can be chosen in implementation, but must be **documented in `README.md`**.

### 2) Seamless use from UI and CLI

- A user can **switch provider / model and run the same kind of operations** (e.g. list models, send a prompt) from **both** Streamlit and the CLI, without ad‑hoc one‑off scripts.
- **Parity rule:** if the UI exposes a capability, the CLI exposes an equivalent; document both in `README.md`.

### 3) Concrete SDK-style operations (minimum “useful” surface)

- **List models** (or the closest equivalent the provider exposes): show identifiers the user can select for a follow-up call.
- **Run a text prompt** (chat/completions-style): user chooses provider, model, and input; display the model response and basic metadata (e.g. errors, latency, or token usage where the API returns it).
- **Optional but valuable** if straightforward for a provider: streaming responses, or a small “connection check” that validates credentials without a full generation.

If a given provider does not support “list models,” document that limitation in `README.md` and provide a **documented** fallback (e.g. a fixed allowlist of model IDs for that provider).

---

## Suggested work breakdown

### Task 1 — Plan (no implementation yet)

- Produce a **detailed requirements and implementation plan** (data flow, module layout, env vars, error handling, and how UI/CLI stay in sync).
- **Do not invent unstated product facts.** If something is ambiguous, **ask the user** before locking the plan.

### Later tasks (after plan approval)

- Implement per the plan; keep `AGENTS.md` / `CLAUDE.md` (same content via symlink) and `README.md` updated as behavior changes.
