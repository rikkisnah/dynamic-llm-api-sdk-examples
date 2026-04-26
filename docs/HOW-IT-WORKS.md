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
2. UI chat can optionally add attachment context and web-research context for the turn.
3. Service layer builds `ChatRequest` (including optional `image_attachments`).
4. Registry resolves provider adapter.
5. Provider adapter calls native SDK (or documented fallback).
6. Provider response is normalized into `ChatResponse`.
7. Surface renders text and metadata.

## Chat Attachments and Multimodal Flow

1. Chat composer accepts uploaded files/images (`+`) and pasted images where browser/Streamlit supports it.
2. Text files are normalized into prompt context text.
3. Images are normalized into `ImageAttachment` objects.
4. Provider adapters map those attachments to provider-native multimodal payloads:
   - OpenAI-compatible (OpenAI, DeepSeek, Qwen, Z.ai)
   - Anthropic blocks (Claude)
   - Gemini `inline_data` parts
5. If a selected model does not support vision, provider adapters return normalized errors.

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
