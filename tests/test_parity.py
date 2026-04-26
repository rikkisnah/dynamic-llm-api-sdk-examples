"""CLI/UI parity tests from capability registry."""

from __future__ import annotations

from llm_examples.capabilities import CAPABILITIES
from llm_examples.cli.parser import cli_param_bindings
from llm_examples.ui.app import UI_PARAM_BINDINGS, ui_capability_names


def test_capability_names_reachable_from_cli_and_ui() -> None:
    expected = {item.name for item in CAPABILITIES}
    cli_names = set(cli_param_bindings().keys())
    ui_names = set(ui_capability_names())
    assert cli_names == expected
    assert ui_names == expected


def test_every_parameter_is_honored_by_cli_and_ui() -> None:
    cli_bindings = cli_param_bindings()
    for capability in CAPABILITIES:
        expected = {param.name for param in capability.params}
        assert set(cli_bindings[capability.name]) == expected
        assert set(UI_PARAM_BINDINGS[capability.name]) == expected
