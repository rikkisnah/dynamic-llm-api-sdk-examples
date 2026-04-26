# ADR 0003: Unified Error Model

## Status

Accepted

## Context

Provider SDK errors differ in shape and semantics.

## Decision

Normalize all failures to `LLMError` with explicit `kind`.

`MissingCredential` subclasses `LLMError(kind="auth")` so config failures use the same path.

CLI exit codes:

- 2: auth
- 3: rate_limit
- 4: bad_request
- 5: network
- 6: server
- 7: unsupported

## Consequences

- Surface code remains simple and consistent.
- JSON error payloads are stable across providers.
