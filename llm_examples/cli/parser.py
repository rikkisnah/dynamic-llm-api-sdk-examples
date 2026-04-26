"""Tier 5: argparse surface generated from capabilities registry."""

from __future__ import annotations

import argparse
from typing import Mapping

from llm_examples.capabilities import CAPABILITIES, Capability, Parameter
from llm_examples.registry import PROVIDERS


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser from declarative capabilities."""
    parser = argparse.ArgumentParser(prog="llm-examples", description="Dynamic multi-provider LLM examples")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for capability in CAPABILITIES:
        sub = subparsers.add_parser(capability.name, help=capability.summary, description=capability.summary)
        sub.add_argument(
            "--json",
            action="store_true",
            default=argparse.SUPPRESS,
            help=argparse.SUPPRESS,
        )
        for parameter in capability.params:
            _add_parameter(sub, parameter)
    return parser


def cli_param_bindings() -> Mapping[str, tuple[str, ...]]:
    """Collect parser-backed parameter names per capability for parity tests."""
    parser = build_parser()
    subparser_action = next(
        action
        for action in parser._actions  # noqa: SLF001 - argparse stores subcommands privately
        if isinstance(action, argparse._SubParsersAction)  # noqa: SLF001
    )
    bindings: dict[str, tuple[str, ...]] = {}
    for name, sub in subparser_action.choices.items():
        params: list[str] = []
        for action in sub._actions:  # noqa: SLF001
            if action.dest in {"help"}:
                continue
            if action.dest in {"json"}:  # pragma: no cover - no subparser-local json action today
                continue
            params.append(action.dest.replace("_", "-"))
        bindings[name] = tuple(params)
    return bindings


def _add_parameter(parser: argparse.ArgumentParser, parameter: Parameter) -> None:
    flag = f"--{parameter.name}"
    dest = parameter.name.replace("-", "_")
    kwargs: dict[str, object] = {"dest": dest, "required": parameter.required, "help": parameter.help}
    if parameter.type == "str" or parameter.type == "path" or parameter.type == "enum:model":
        kwargs["type"] = str
        if parameter.default is not None:
            kwargs["default"] = parameter.default
        parser.add_argument(flag, **kwargs)
        return
    if parameter.type == "int":
        kwargs["type"] = int
        if parameter.default is not None:
            kwargs["default"] = parameter.default
        parser.add_argument(flag, **kwargs)
        return
    if parameter.type == "bool":
        kwargs.pop("required", None)
        kwargs["action"] = argparse.BooleanOptionalAction
        if parameter.default is not None:
            kwargs["default"] = parameter.default
        parser.add_argument(flag, **kwargs)
        return
    if parameter.type == "enum:provider":
        kwargs["choices"] = PROVIDERS
        parser.add_argument(flag, **kwargs)
        return
    raise ValueError(f"Unsupported parameter type for {parameter.name}: {parameter.type}")


def capability_names() -> tuple[str, ...]:
    """List known capability names used by parser."""
    return tuple(capability.name for capability in CAPABILITIES)


def capabilities_by_name() -> Mapping[str, Capability]:
    """Expose capabilities by name for tests and help generation."""
    return {capability.name: capability for capability in CAPABILITIES}
