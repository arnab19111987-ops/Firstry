# firsttry/quickfix.py
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .doctor import CheckResult


def _rule_missing_database_url(output: str) -> list[str]:
    """If env / DATABASE_URL / connection string issues appear,
    suggest sqlite fallback for local dev.
    """
    hits = []
    patterns = [
        r"DATABASE_URL",
        r"KeyError:\s*'DATABASE_URL'",
        r"could not connect to server: Connection refused",
    ]
    if any(re.search(p, output, re.IGNORECASE) for p in patterns):
        hits.append(
            "No DATABASE_URL? Create a local .env.development with:\n"
            "  DATABASE_URL=sqlite:///./.firsttry.db\n"
            "Then re-run firsttry doctor.",
        )
    return hits


def _rule_import_error(output: str) -> list[str]:
    """Import errors --> tell user to expose symbol or install package."""
    hits = []
    if "ModuleNotFoundError" in output or "ImportError" in output:
        hits.append(
            "Import error detected. Fix by ensuring the module is importable "
            "(add __init__.py or re-export missing symbols).",
        )
    return hits


def _rule_ruff_unused_import(output: str) -> list[str]:
    """Ruff unused-import / lint issues --> show autofix command."""
    hits = []
    if "unused import" in output.lower() or "F401" in output:
        hits.append(
            "Ruff reports unused imports. Auto-fix with:\n"
            "  ruff check . --fix\n"
            "Then commit the changes.",
        )
    return hits


def _rule_black_reformat(output: str) -> list[str]:
    hits = []
    if "would reformat" in output or "reformatted" in output:
        hits.append("Black formatting needed. Run:\n  black .")
    return hits


def _rule_mypy_hint(output: str) -> list[str]:
    hits = []
    if "error:" in output and "mypy" in output.lower():
        hits.append(
            "Mypy type errors found. Add/adjust type hints, or mark "
            "# type: ignore for intentional dynamic code.",
        )
    return hits


def generate_quickfix_suggestions(checks: list[CheckResult]) -> list[str]:
    """Look at failing CheckResult outputs and offer human-friendly fixes.
    Dedup messages while preserving order.
    """
    suggestions: list[str] = []

    rules = [
        _rule_missing_database_url,
        _rule_import_error,
        _rule_ruff_unused_import,
        _rule_black_reformat,
        _rule_mypy_hint,
    ]

    for c in checks:
        if c.passed:
            continue
        for rule in rules:
            for msg in rule(c.output):
                if msg not in suggestions:
                    suggestions.append(msg)

        # Always include the check's own fix_hint (if defined)
        if c.fix_hint and c.fix_hint not in suggestions:
            suggestions.append(c.fix_hint)

    return suggestions
