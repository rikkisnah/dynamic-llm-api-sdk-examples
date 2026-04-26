"""Tier 5: CLI output helpers."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping


def print_json(payload: Mapping[str, object]) -> None:
    """Print stable JSON payload with newline."""
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")


def print_lines(lines: Iterable[str]) -> None:
    """Print one line per item."""
    for line in lines:
        sys.stdout.write(f"{line}\n")
