"""Tier 5: Command dispatch table."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable, Mapping

from llm_examples.cli.cmd_check import handle_check
from llm_examples.cli.cmd_list import handle_list_models
from llm_examples.cli.cmd_providers import handle_providers
from llm_examples.cli.cmd_run import handle_run
from llm_examples.cli.errors import emit_error
from llm_examples.domain_types import LLMError

CommandHandler = Callable[[Namespace], int]

COMMANDS: Mapping[str, CommandHandler] = {
    "providers": handle_providers,
    "list-models": handle_list_models,
    "run": handle_run,
    "check": handle_check,
}


def dispatch(args: Namespace) -> int:
    """Run selected command with normalized error handling."""
    handler = COMMANDS.get(args.command)
    if handler is None:
        raise LLMError(
            provider="openai",
            model=None,
            kind="bad_request",
            message=f"Unknown command: {args.command}",
        )
    try:
        return handler(args)
    except LLMError as error:
        return emit_error(error, json_output=args.json)
