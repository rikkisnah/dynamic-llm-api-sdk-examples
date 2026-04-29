"""Tier 0: Single-source capability and parameter registry for CLI and UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ParameterType = Literal["str", "int", "bool", "path", "enum:provider", "enum:model"]


@dataclass(frozen=True, slots=True)
class Parameter:
    """Declarative description of one command/form parameter."""

    name: str
    type: ParameterType
    required: bool = False
    default: object | None = None
    help: str = ""


@dataclass(frozen=True, slots=True)
class Capability:
    """Declarative description of one feature available in CLI and UI."""

    name: str
    summary: str
    params: tuple[Parameter, ...]
    json_output: bool = True
    streams: bool = False


CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        name="providers",
        summary="List configured providers",
        params=(),
    ),
    Capability(
        name="list-models",
        summary="List models for a provider",
        params=(
            Parameter(
                name="provider",
                type="enum:provider",
                required=False,
                help=(
                    "Provider name to query for available models. "
                    "Defaults to AI_PROVIDER / DEFAULT_AI_PROVIDER from .env when omitted."
                ),
            ),
        ),
    ),
    Capability(
        name="run",
        summary="Run a one-shot prompt",
        params=(
            Parameter(
                name="provider",
                type="enum:provider",
                required=False,
                help=(
                    "Provider name to run the prompt with. "
                    "Defaults to AI_PROVIDER / DEFAULT_AI_PROVIDER from .env when omitted."
                ),
            ),
            Parameter(
                name="model",
                type="enum:model",
                required=False,
                help="Model identifier. Defaults to provider default if omitted.",
            ),
            Parameter(
                name="prompt",
                type="str",
                required=False,
                help="Prompt text. Mutually exclusive with --prompt-file.",
            ),
            Parameter(
                name="prompt-file",
                type="path",
                required=False,
                help="Path to prompt file. Use '-' to read prompt from stdin.",
            ),
            Parameter(
                name="system",
                type="str",
                required=False,
                help="Optional system instruction for chat-capable providers.",
            ),
            Parameter(
                name="max-tokens",
                type="int",
                required=False,
                default=512,
                help="Maximum output token budget.",
            ),
            Parameter(
                name="stream",
                type="bool",
                required=False,
                default=False,
                help="Enable token streaming when provider supports it.",
            ),
        ),
        streams=True,
    ),
    Capability(
        name="check",
        summary="Validate credentials for a provider",
        params=(
            Parameter(
                name="provider",
                type="enum:provider",
                required=False,
                help=(
                    "Provider name whose credentials should be validated. "
                    "Defaults to AI_PROVIDER / DEFAULT_AI_PROVIDER from .env when omitted."
                ),
            ),
        ),
    ),
)


def capability_by_name(name: str) -> Capability:
    """Lookup helper used by both surfaces."""
    for capability in CAPABILITIES:
        if capability.name == name:
            return capability
    raise KeyError(name)
