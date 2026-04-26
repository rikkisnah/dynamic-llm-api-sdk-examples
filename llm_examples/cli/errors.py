"""Tier 5: CLI error formatting and exit code mapping."""

from __future__ import annotations

import json
import sys
from typing import Mapping

from llm_examples.domain_types import LLMError

EXIT_CODES: Mapping[str, int] = {
    "auth": 2,
    "rate_limit": 3,
    "bad_request": 4,
    "network": 5,
    "server": 6,
    "unsupported": 7,
}


def emit_error(error: LLMError, *, json_output: bool) -> int:
    """Print normalized errors in either human or machine-readable shape."""
    code = EXIT_CODES.get(error.kind, 6)
    if json_output:
        payload = {"ok": False, "error": dict(error.to_dict())}
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stderr.write(f"{error.kind}: {error.message}\n")
    return code
