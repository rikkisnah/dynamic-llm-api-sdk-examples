"""Regression test: every public Make target appears in `make help`.

`Makefile` declares its public targets in `.PHONY`. Each one must carry an
inline `## description` so the auto-generated `help` target picks it up;
section grouping uses `##@ Section` markers. The pattern target `test-%` is
allowed to keep its `%` placeholder in the help line.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

# These appear in `.PHONY` but are not standalone user-facing targets:
#   - `test-%` is exposed in help, but its concrete invocation pattern is
#     captured separately so we don't require a literal `test-%:` rule.
PHONY_TARGETS_THAT_ARE_PATTERNS = {"test-%"}


def _read_makefile() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def _phony_targets() -> set[str]:
    text = _read_makefile()
    matches = re.findall(r"^\.PHONY:\s*(.+)$", text, flags=re.MULTILINE)
    targets: set[str] = set()
    for line in matches:
        for token in line.split():
            targets.add(token)
    return targets


def _annotated_targets() -> dict[str, str]:
    """Map of target name → description for every `name: ## desc` line."""
    text = _read_makefile()
    rows: dict[str, str] = {}
    for match in re.finditer(
        r"^(?P<name>[a-zA-Z_%][a-zA-Z0-9_%-]*)\s*:[^#\n]*##\s*(?P<desc>.+)$",
        text,
        flags=re.MULTILINE,
    ):
        rows[match.group("name")] = match.group("desc").strip()
    return rows


def test_every_phony_target_has_a_help_annotation() -> None:
    annotated = _annotated_targets()
    missing = sorted(
        target
        for target in _phony_targets()
        if target not in annotated and target not in PHONY_TARGETS_THAT_ARE_PATTERNS
    )
    assert not missing, (
        f"Make targets missing `## description` annotation: {missing}. "
        "Every `.PHONY` target must carry one so it appears in `make help`."
    )


def test_help_target_is_self_documenting() -> None:
    annotated = _annotated_targets()
    assert "help" in annotated
    assert "auto-generated" in annotated["help"].lower()


def test_help_recipe_uses_makefile_list_for_awk_parsing() -> None:
    text = _read_makefile()
    assert "MAKEFILE_LIST" in text, (
        "`make help` must parse $(MAKEFILE_LIST) so includes/overlays are picked up."
    )
    assert re.search(r"^##@\s+\w", text, flags=re.MULTILINE), (
        "Section headers (`##@ Section`) are required for the auto-generated help layout."
    )


def test_pattern_target_is_documented_even_though_phony_lists_a_placeholder() -> None:
    text = _read_makefile()
    # The literal pattern rule `test-%:` must exist with an annotation so the
    # help line `test-%   run a single test file: make test-providers ...`
    # is generated.
    assert re.search(r"^test-%:[^#\n]*##\s*\S", text, flags=re.MULTILINE), (
        "`test-%:` pattern rule must carry a `## description` for help."
    )
