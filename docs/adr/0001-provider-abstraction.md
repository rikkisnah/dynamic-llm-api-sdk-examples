# ADR 0001: Provider Abstraction

## Status

Accepted

## Context

The product must demonstrate vendor-specific SDK usage across six providers while also exposing a single CLI/UI workflow.

## Decision

Use per-provider adapters that implement a shared `BaseClient` interface.

- OpenAI: native `openai`
- Claude: native `anthropic`
- Gemini: native `google-genai`
- Qwen: OpenAI-compatible path via `openai` SDK + DashScope compatible-mode endpoint
- DeepSeek: OpenAI-compatible path via `openai` SDK + DeepSeek base URL
- Z.ai: prefer `zai-sdk`, fallback to documented OpenAI-compatible HTTP endpoint

## Consequences

- Vendor quirks are isolated to tier-2 modules.
- Service and surface layers stay provider-agnostic.
