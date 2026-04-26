"""Tier 5: UI formatting helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Mapping

from llm_examples.domain_types import ChatResponse, CheckResult, LLMError, ModelInfo


def to_json_payload(value: object) -> Mapping[str, object]:
    """Convert known response objects into JSON-friendly mappings."""
    if isinstance(value, LLMError):
        return dict(value.to_dict())
    if isinstance(value, ChatResponse):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, CheckResult):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, ModelInfo):
        payload = asdict(value) if is_dataclass(value) else {}
        return payload
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def pretty_json(payload: Mapping[str, object]) -> str:
    """Render stable JSON for Streamlit code blocks."""
    return json.dumps(payload, indent=2)
