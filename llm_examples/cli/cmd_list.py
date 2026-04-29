"""Tier 5: `list-models` command handler."""

from __future__ import annotations

from argparse import Namespace

from llm_examples.cli.output import print_json, print_lines
from llm_examples.cli.providers import resolve_provider
from llm_examples.services import list_models


def handle_list_models(args: Namespace) -> int:
    """List models for a given provider."""
    provider = resolve_provider(args.provider)
    models = list_models(provider)
    if args.json:
        payload = {
            "ok": True,
            "provider": provider,
            "models": [{"id": item.id, "description": item.description} for item in models],
        }
        print_json(payload)
    else:
        print_lines([item.id for item in models])
    return 0
