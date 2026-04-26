"""Tier 5: `check` command handler."""

from __future__ import annotations

from argparse import Namespace

from llm_examples.services import check_connection

from llm_examples.cli.output import print_json, print_lines


def handle_check(args: Namespace) -> int:
    """Run a lightweight credential check for a provider."""
    result = check_connection(args.provider)
    if args.json:
        print_json(
            {
                "ok": result.ok,
                "provider": result.provider,
                "latency_ms": result.latency_ms,
                "detail": result.detail,
            }
        )
    else:
        print_lines([f"{result.provider}: {result.detail} ({result.latency_ms:.1f} ms)"])
    return 0
