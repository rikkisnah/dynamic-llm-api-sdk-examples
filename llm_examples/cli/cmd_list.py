"""Tier 5: `list-models` command handler."""

from __future__ import annotations

from argparse import Namespace

from llm_examples.services import list_models

from llm_examples.cli.output import print_json, print_lines


def handle_list_models(args: Namespace) -> int:
    """List models for a given provider."""
    models = list_models(args.provider)
    if args.json:
        payload = {
            "ok": True,
            "provider": args.provider,
            "models": [{"id": item.id, "description": item.description} for item in models],
        }
        print_json(payload)
    else:
        print_lines([item.id for item in models])
    return 0
