"""Tier 5: CLI entry point."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from llm_examples.cli.commands import dispatch
from llm_examples.cli.parser import build_parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for `llm-examples`."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return dispatch(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
