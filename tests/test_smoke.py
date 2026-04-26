"""Smoke tests for package importability."""

from __future__ import annotations


def test_import_package() -> None:
    import llm_examples  # noqa: F401
