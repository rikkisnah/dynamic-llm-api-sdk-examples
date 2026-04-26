# ADR 0005: Standalone Examples vs Package Adapters

## Status

Accepted

## Context

Users need both:

1. Production-shaped adapters for parity-safe CLI/UI integration.
2. Copyable, one-file SDK examples per provider.

## Decision

Maintain both surfaces:

- `llm_examples/providers/*_provider.py`: package adapters inside tiered architecture.
- `examples/*_example.py`: standalone scripts with no `llm_examples` import.

## Consequences

- Learning and integration use-cases are both covered.
- Changes to provider behavior should be reflected in both adapter and standalone script.
