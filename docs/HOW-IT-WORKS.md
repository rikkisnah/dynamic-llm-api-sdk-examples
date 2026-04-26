# How It Works

## Tiered Architecture

1. Tier 0: domain/config/capability types
2. Tier 1: provider interface (`BaseClient`)
3. Tier 2: provider adapters
4. Tier 3: provider registry
5. Tier 4: service layer
6. Tier 5: CLI and Streamlit surfaces

UI and CLI only call `llm_examples.services`.

## Request Lifecycle

1. CLI or UI collects provider/model/prompt.
2. Service layer builds `ChatRequest`.
3. Registry resolves provider adapter.
4. Provider adapter calls native SDK (or documented fallback).
5. Provider response is normalized into `ChatResponse`.
6. Surface renders text and metadata.

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
