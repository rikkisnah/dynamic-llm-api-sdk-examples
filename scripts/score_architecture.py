"""Architecture scorecard for dynamic-llm-api-sdk-examples."""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class DimensionResult:
    name: str
    score: int
    notes: str


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if ".venv" not in path.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _score_readability(root: Path) -> DimensionResult:
    files = _python_files(root / "llm_examples") + _python_files(root / "tests") + _python_files(root / "scripts")
    max_lines = max((len(_read(path).splitlines()) for path in files), default=0)
    long_functions = 0
    deep_functions = 0
    missing_docstrings = 0
    for path in files:
        source = _read(path)
        tree = ast.parse(source)
        if ast.get_docstring(tree) is None:
            missing_docstrings += 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (
                    max((getattr(child, "lineno", node.lineno) for child in ast.walk(node)), default=node.lineno)
                    - node.lineno
                )
                if length > 100:
                    long_functions += 1
                if _max_nesting(node) > 5:
                    deep_functions += 1
    penalties = 0
    penalties += 0 if max_lines <= 800 else 2
    penalties += min(long_functions, 4)
    penalties += min(deep_functions, 4)
    penalties += min(missing_docstrings, 4)
    score = max(0, 10 - penalties)
    notes = f"max_lines={max_lines}, long_functions={long_functions}, deep_functions={deep_functions}, missing_docstrings={missing_docstrings}"
    return DimensionResult("Readability", score, notes)


def _max_nesting(node: ast.AST) -> int:
    max_depth = 0

    def walk(current: ast.AST, depth: int) -> None:
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match)):
                walk(child, depth + 1)
            else:
                walk(child, depth)

    walk(node, 0)
    return max_depth


def _score_modularity(root: Path) -> DimensionResult:
    package_init = root / "llm_examples" / "__init__.py"
    init_ok = package_init.exists() and all(
        line.startswith(("from ", "__all__", "\"\"\"", "", "#"))
        for line in _read(package_init).splitlines()
    )
    importable = _package_importable(root)

    upward_imports = _find_tier_violations(root)
    penalties = 0
    penalties += 0 if init_ok else 3
    penalties += 0 if importable else 4
    penalties += min(len(upward_imports), 4)
    score = max(0, 10 - penalties)
    notes = f"init_ok={init_ok}, importable={importable}, upward_imports={len(upward_imports)}"
    return DimensionResult("Modularity", score, notes)


def _find_tier_violations(root: Path) -> list[str]:
    tiers = {
        "domain_types": 0,
        "config": 0,
        "capabilities": 0,
        "llm_client": 1,
        "providers": 2,
        "registry": 3,
        "services": 4,
        "cli": 5,
        "ui": 5,
    }
    violations: list[str] = []
    for path in _python_files(root / "llm_examples"):
        relative = path.relative_to(root / "llm_examples")
        top = relative.parts[0]
        module_tier = tiers.get(top.replace(".py", ""), tiers.get(path.stem, 5))
        source = _read(path)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if not module.startswith("llm_examples."):
                continue
            target = module.split(".")[1]
            target_tier = tiers.get(target, 5)
            if target_tier > module_tier:
                violations.append(f"{relative}:{node.lineno} imports {module}")
    return violations


def _score_scalability(root: Path) -> DimensionResult:
    provider_modules = list((root / "llm_examples" / "providers").glob("*_provider.py"))
    cli_dispatch = (root / "llm_examples" / "cli" / "commands.py").exists()
    capabilities = (root / "llm_examples" / "capabilities.py").exists()
    score = 10
    if len(provider_modules) < 6:
        score -= 4
    if not cli_dispatch:
        score -= 3
    if not capabilities:
        score -= 3
    notes = f"provider_modules={len(provider_modules)}, cli_dispatch={cli_dispatch}, capabilities={capabilities}"
    return DimensionResult("Scalability", max(0, score), notes)


def _score_test_quality(root: Path) -> DimensionResult:
    pyproject = _read(root / "pyproject.toml") if (root / "pyproject.toml").exists() else ""
    has_cov_gate = "cov-fail-under=100" in pyproject
    required = ["helpers.py", "conftest.py", "test_smoke.py"]
    required_ok = all((root / "tests" / name).exists() for name in required)
    test_files = _python_files(root / "tests")
    parametrize_hits = sum("@pytest.mark.parametrize" in _read(path) for path in test_files)
    penalties = 0
    penalties += 0 if has_cov_gate else 4
    penalties += 0 if required_ok else 3
    penalties += 0 if parametrize_hits >= 3 else 3
    notes = f"cov_gate={has_cov_gate}, required_ok={required_ok}, parametrize_hits={parametrize_hits}"
    return DimensionResult("Test Quality", max(0, 10 - penalties), notes)


def _score_documentation(root: Path) -> DimensionResult:
    required_docs = [
        root / "README.md",
        root / "docs" / "INSTALL.md",
        root / "docs" / "USAGE.md",
        root / "docs" / "HOW-IT-WORKS.md",
        root / "docs" / "PLAN.md",
    ]
    docs_ok = all(path.exists() for path in required_docs)
    adr_count = len(list((root / "docs" / "adr").glob("*.md")))
    tier_doc_ok = True
    for path in _python_files(root / "llm_examples"):
        module_doc = ast.get_docstring(ast.parse(_read(path))) or ""
        if "Tier " not in module_doc:
            tier_doc_ok = False
            break
    score = 10
    if not docs_ok:
        score -= 4
    if adr_count < 5:
        score -= 3
    if not tier_doc_ok:
        score -= 3
    notes = f"docs_ok={docs_ok}, adr_count={adr_count}, tier_doc_ok={tier_doc_ok}"
    return DimensionResult("Documentation", max(0, score), notes)


def _score_build_and_packaging(root: Path) -> DimensionResult:
    makefile = _read(root / "Makefile") if (root / "Makefile").exists() else ""
    has_check = "check: lint lint-imports type test score" in makefile
    has_test_rule = "test-%:" in makefile
    has_lint_imports = "lint-imports:" in makefile
    has_mypy_strict = "--strict llm_examples/" in makefile
    importable = _package_importable(root)
    score = 10
    if not has_check:
        score -= 3
    if not has_test_rule:
        score -= 2
    if not has_lint_imports:
        score -= 2
    if not has_mypy_strict:
        score -= 2
    if not importable:
        score -= 1
    notes = f"has_check={has_check}, has_test_rule={has_test_rule}, has_lint_imports={has_lint_imports}, has_mypy_strict={has_mypy_strict}, importable={importable}"
    return DimensionResult("Build & Packaging", max(0, score), notes)


def _score_type_safety(root: Path) -> DimensionResult:
    domain_types = root / "llm_examples" / "domain_types.py"
    imports = 0
    for path in _python_files(root / "llm_examples"):
        if "from llm_examples.domain_types import" in _read(path):
            imports += 1
    dict_any_hits = 0
    pattern = re.compile(r"dict\[\s*str\s*,\s*Any\s*\]")
    for path in _python_files(root / "llm_examples"):
        dict_any_hits += len(pattern.findall(_read(path)))
    score = 10
    if not domain_types.exists():
        score -= 5
    if imports < 4:
        score -= 3
    if dict_any_hits > 0:
        score -= 2
    notes = f"domain_types={domain_types.exists()}, imports={imports}, dict_any_hits={dict_any_hits}"
    return DimensionResult("Type Safety", max(0, score), notes)


def _score_duplication(root: Path) -> DimensionResult:
    provider_files = sorted((root / "llm_examples" / "providers").glob("*_provider.py"))
    top_level_defs: dict[str, int] = {}
    for path in provider_files:
        tree = ast.parse(_read(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                top_level_defs[node.name] = top_level_defs.get(node.name, 0) + 1
    duplicated_defs = sum(1 for count in top_level_defs.values() if count > 1)
    services_path = root / "llm_examples" / "services.py"
    services_lines = len(_read(services_path).splitlines()) if services_path.exists() else 10_000
    score = 10
    if duplicated_defs > 0:
        score -= 3
    if services_lines > 200:
        score -= 4
    notes = f"duplicated_defs={duplicated_defs}, services_lines={services_lines}"
    return DimensionResult("Code Duplication", max(0, score), notes)


def _score_agent_discoverability(root: Path) -> DimensionResult:
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    symlink_ok = agents.is_symlink() and agents.resolve() == claude.resolve()
    readme = _read(root / "README.md") if (root / "README.md").exists() else ""
    commands_table = "| Command | CLI | UI |" in readme
    env_table = "| Provider | API key env | Base URL env |" in readme
    plan = _read(root / "docs" / "PLAN.md") if (root / "docs" / "PLAN.md").exists() else ""
    providers_mentioned = all(name in plan for name in ["OpenAI", "Claude", "Gemini", "DeepSeek", "Qwen", "Z.ai"])
    score = 10
    if not symlink_ok:
        score -= 4
    if not commands_table:
        score -= 3
    if not env_table:
        score -= 2
    if not providers_mentioned:
        score -= 1
    notes = f"symlink_ok={symlink_ok}, commands_table={commands_table}, env_table={env_table}, providers_mentioned={providers_mentioned}"
    return DimensionResult("Agent Discoverability", max(0, score), notes)


def _score_provider_symmetry(root: Path) -> DimensionResult:
    provider_files = sorted((root / "llm_examples" / "providers").glob("*_provider.py"))
    example_files = sorted((root / "examples").glob("*_example.py"))
    symmetry_ok = len(provider_files) >= 6 and len(example_files) >= 6
    tests_path = root / "tests" / "test_providers.py"
    tests_text = _read(tests_path) if tests_path.exists() else ""
    has_param_rows = tests_text.count("provider_name") >= 1 and "@pytest.mark.parametrize" in tests_text
    score = 10
    if not symmetry_ok:
        score -= 5
    if not has_param_rows:
        score -= 3
    notes = f"provider_files={len(provider_files)}, example_files={len(example_files)}, has_param_rows={has_param_rows}"
    return DimensionResult("Provider Symmetry", max(0, score), notes)


def _score_parity(root: Path) -> DimensionResult:
    parser_path = root / "llm_examples" / "cli" / "parser.py"
    ui_path = root / "llm_examples" / "ui" / "app.py"
    parser_text = _read(parser_path) if parser_path.exists() else ""
    ui_text = _read(ui_path) if ui_path.exists() else ""
    uses_capabilities = "CAPABILITIES" in parser_text and "CAPABILITIES" in ui_text
    parity_test_exists = (root / "tests" / "test_parity.py").exists()
    score = 10
    if not uses_capabilities:
        score -= 6
    if not parity_test_exists:
        score -= 4
    notes = f"uses_capabilities={uses_capabilities}, parity_test_exists={parity_test_exists}"
    return DimensionResult("CLI/UI Parity", max(0, score), notes)


def _score_secret_hygiene(root: Path) -> DimensionResult:
    gitignore = _read(root / ".gitignore") if (root / ".gitignore").exists() else ""
    env_gitignored = ".env" in gitignore
    env_example = _read(root / ".env.example") if (root / ".env.example").exists() else ""
    all_keys = all(
        key in env_example
        for key in [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "DEEPSEEK_API_KEY",
            "DASHSCOPE_API_KEY",
            "ZAI_API_KEY",
        ]
    )
    lock_exists = (root / "uv.lock").exists()
    source_text = "\n".join(_read(path) for path in _python_files(root / "llm_examples"))
    hardcoded_key = bool(re.search(r"sk-[A-Za-z0-9]{16,}", source_text))
    conftest = _read(root / "tests" / "conftest.py") if (root / "tests" / "conftest.py").exists() else ""
    network_disabled = "create_connection" in conftest
    score = 10
    if not env_gitignored:
        score -= 3
    if not all_keys:
        score -= 3
    if not lock_exists:
        score -= 2
    if hardcoded_key:
        score -= 1
    if not network_disabled:
        score -= 1
    notes = f"env_gitignored={env_gitignored}, all_keys={all_keys}, lock_exists={lock_exists}, hardcoded_key={hardcoded_key}, network_disabled={network_disabled}"
    return DimensionResult("Secret Hygiene & Reproducibility", max(0, score), notes)


DIMENSIONS: tuple[Callable[[Path], DimensionResult], ...] = (
    _score_readability,
    _score_modularity,
    _score_scalability,
    _score_test_quality,
    _score_documentation,
    _score_build_and_packaging,
    _score_type_safety,
    _score_duplication,
    _score_agent_discoverability,
    _score_provider_symmetry,
    _score_parity,
    _score_secret_hygiene,
)


def _package_importable(root: Path) -> bool:
    try:
        importlib.import_module("llm_examples")
        return True
    except Exception:
        pass
    result = subprocess.run(
        [sys.executable, "-c", "import llm_examples"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def score_project(root: Path) -> list[DimensionResult]:
    """Compute all dimension scores."""
    return [dimension(root) for dimension in DIMENSIONS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--min-score", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    results = score_project(args.root)
    payload = {
        "results": [{"name": result.name, "score": result.score, "notes": result.notes} for result in results],
        "min_score": args.min_score,
    }
    if args.json:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        for result in results:
            sys.stdout.write(f"{result.name:34} {result.score}/10  {result.notes}\n")
    failed = [result for result in results if result.score < args.min_score]
    if failed:
        sys.stderr.write("score gate failed\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
