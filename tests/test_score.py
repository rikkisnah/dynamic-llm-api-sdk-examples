"""Architecture score gate tests."""

from __future__ import annotations

from pathlib import Path

from scripts.score_architecture import score_project


def test_every_dimension_meets_minimum() -> None:
    results = score_project(Path(__file__).resolve().parents[1])
    assert len(results) == 12
    assert all(item.score >= 8 for item in results), results
