"""Tier 5: `providers` command handler."""

from __future__ import annotations

from argparse import Namespace

from llm_examples.cli.output import print_json, print_lines
from llm_examples.config import get_provider_config, provider_env_names
from llm_examples.domain_types import MissingCredential
from llm_examples.registry import PROVIDERS


def handle_providers(args: Namespace) -> int:
    """List providers and whether keys are currently configured."""
    rows: list[dict[str, object]] = []
    for provider in PROVIDERS:
        api_key_env, _ = provider_env_names(provider)
        configured = True
        try:
            _ = get_provider_config(provider)
        except MissingCredential:
            configured = False
        rows.append({"provider": provider, "configured": configured, "api_key_env": api_key_env})

    if args.json:
        print_json({"ok": True, "providers": rows})
    else:
        lines = [
            f"{row['provider']}: {'configured' if row['configured'] else 'missing key'}"
            for row in rows
        ]
        print_lines(lines)
    return 0
