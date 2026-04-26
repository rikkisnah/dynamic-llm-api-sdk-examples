"""Capability registry consistency tests."""

from __future__ import annotations

from llm_examples.capabilities import CAPABILITIES


def test_capability_names_unique() -> None:
    names = [item.name for item in CAPABILITIES]
    assert len(names) == len(set(names))


def test_parameter_names_unique_per_capability() -> None:
    for capability in CAPABILITIES:
        names = [param.name for param in capability.params]
        assert len(names) == len(set(names))


def test_every_parameter_has_help() -> None:
    for capability in CAPABILITIES:
        for parameter in capability.params:
            assert parameter.help.strip(), f"Missing help text for {capability.name}:{parameter.name}"


def test_streaming_capability_has_stream_parameter() -> None:
    for capability in CAPABILITIES:
        if not capability.streams:
            continue
        names = [param.name for param in capability.params]
        assert "stream" in names
