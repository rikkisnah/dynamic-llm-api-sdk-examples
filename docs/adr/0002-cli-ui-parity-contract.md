# ADR 0002: CLI/UI Parity Contract

## Status

Accepted

## Context

CLI and UI parity drifts when each surface manually defines capabilities.

## Decision

Define capabilities once in `llm_examples.capabilities.CAPABILITIES`.

- CLI parser is generated from this registry.
- Streamlit renderers are keyed to this registry.
- Tests enforce command-level and parameter-level parity.

## Consequences

- Adding a new capability requires one registry update.
- Drift becomes a test failure.
