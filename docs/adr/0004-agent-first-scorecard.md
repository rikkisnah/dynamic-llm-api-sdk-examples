# ADR 0004: Agent-First Architecture Scorecard

## Status

Accepted

## Context

This repository is intended to be maintained by both humans and coding agents. A static quality gate reduces ambiguity across sessions.

## Decision

Adopt a 12-dimension architecture score:

1. Readability
2. Modularity
3. Scalability
4. Test Quality
5. Documentation
6. Build & Packaging
7. Type Safety
8. Code Duplication
9. Agent Discoverability
10. Provider Symmetry
11. CLI/UI Parity
12. Secret Hygiene & Reproducibility

Every dimension must score at least 8 in CI.

## Consequences

- Non-functional regressions are surfaced early.
- Agent sessions have a concrete acceptance contract.
