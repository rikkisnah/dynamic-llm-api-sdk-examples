"""Tier 5: argparse surface generated from capabilities registry."""

from __future__ import annotations

import argparse
from collections.abc import Mapping

from llm_examples.capabilities import CAPABILITIES, Capability, Parameter
from llm_examples.config import get_app_version
from llm_examples.registry import PROVIDERS


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser from declarative capabilities."""
    parser = argparse.ArgumentParser(
        prog="llm-examples", description="Dynamic multi-provider LLM examples"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_app_version()}",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for capability in CAPABILITIES:
        sub = subparsers.add_parser(
            capability.name, help=capability.summary, description=capability.summary
        )
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
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    bindings: dict[str, tuple[str, ...]] = {}
    for name, sub in subparser_action.choices.items():
        params: list[str] = []
        for action in sub._actions:
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
    if parameter.type == "str" or parameter.type == "path" or parameter.type == "enum:model":
        if parameter.default is None:
            parser.add_argument(
                flag,
                dest=dest,
                required=parameter.required,
                help=parameter.help,
                type=str,
            )
        else:
            parser.add_argument(
                flag,
                dest=dest,
                required=parameter.required,
                help=parameter.help,
                type=str,
                default=parameter.default,
            )
        return
    if parameter.type == "int":
        if parameter.default is None:
            parser.add_argument(
                flag,
                dest=dest,
                required=parameter.required,
                help=parameter.help,
                type=int,
            )
        else:
            parser.add_argument(
                flag,
                dest=dest,
                required=parameter.required,
                help=parameter.help,
                type=int,
                default=parameter.default,
            )
        return
    if parameter.type == "bool":
        if parameter.default is None:
            parser.add_argument(
                flag,
                dest=dest,
                help=parameter.help,
                action=argparse.BooleanOptionalAction,
            )
        else:
            parser.add_argument(
                flag,
                dest=dest,
                help=parameter.help,
                action=argparse.BooleanOptionalAction,
                default=parameter.default,
            )
        return
    if parameter.type == "enum:provider":
        parser.add_argument(
            flag,
            dest=dest,
            required=parameter.required,
            help=parameter.help,
            choices=PROVIDERS,
        )
        return
    raise ValueError(f"Unsupported parameter type for {parameter.name}: {parameter.type}")


def capability_names() -> tuple[str, ...]:
    """List known capability names used by parser."""
    return tuple(capability.name for capability in CAPABILITIES)


def capabilities_by_name() -> Mapping[str, Capability]:
    """Expose capabilities by name for tests and help generation."""
    return {capability.name: capability for capability in CAPABILITIES}
