"""
quickfix.py
-----------

Given a failing CI step (command + stdout + stderr), try to produce
a short, copy-pasteable human hint that fixes the failure fast.

This powers the `failed_at.hint` field in `firsttry mirror-ci --run` output.

If no known pattern matches, return None and the caller falls back
to a generic "run this command locally" hint.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .doctor import CheckResult


def _rule_missing_database_url(output: str) -> List[str]:
    """
    If env / DATABASE_URL / connection string issues appear,
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
            "Then re-run firsttry doctor."
        )
    return hits


def _rule_import_error(output: str) -> List[str]:
    """
    Import errors --> tell user to expose symbol or install package.
    """
    hits = []
    if "ModuleNotFoundError" in output or "ImportError" in output:
        hits.append(
            "Import error detected. Fix by ensuring the module is importable "
            "(add __init__.py or re-export missing symbols)."
        )
    return hits


def _rule_ruff_unused_import(output: str) -> List[str]:
    """
    Ruff unused-import / lint issues --> show autofix command.
    """
    hits = []
    if "unused import" in output.lower() or "F401" in output:
        hits.append(
            "Ruff reports unused imports. Auto-fix with:\n"
            "  ruff check . --fix\n"
            "Then commit the changes."
        )
    return hits


def _rule_black_reformat(output: str) -> List[str]:
    hits = []
    if "would reformat" in output or "reformatted" in output:
        hits.append("Black formatting needed. Run:\n" "  black .")
    return hits


def _rule_mypy_hint(output: str) -> List[str]:
    hits = []
    if "error:" in output and "mypy" in output.lower():
        hits.append(
            "Mypy type errors found. Add/adjust type hints, or mark "
            "# type: ignore for intentional dynamic code."
        )
    return hits


def generate_quickfix_suggestions(checks: List[CheckResult]) -> List[str]:
    """
    Look at failing CheckResult outputs and offer human-friendly fixes.
    Dedup messages while preserving order.
    """
    suggestions: List[str] = []

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


def suggest_fix(cmd: str, stdout: str, stderr: str) -> str | None:
    """
    Heuristic quick-fix suggestion for a failing CI step.

    Returns a short, actionable hint string or None when no suggestion applies.
    This is intentionally conservative and best-effort.
    """
    import re

    combined = (stdout or "") + "\n" + (stderr or "")
    lower = combined.lower().strip()
    cmd_l = (cmd or "").lower()

    # 1. Tool not found (ruff / black / pytest)
    if "ruff" in cmd_l and ("command not found" in lower or "not found" in lower):
        return "Ruff is not installed locally. Run: pip install ruff  # then re-run firsttry"
    if "black" in cmd_l and ("command not found" in lower or "not found" in lower):
        return "Black is not installed locally. Run: pip install black  # then re-run firsttry"
    if "pytest" in cmd_l and ("command not found" in lower or "not found" in lower):
        return "Pytest is not installed locally. Run: pip install pytest  # then re-run firsttry"

    # 2. ImportError / ModuleNotFoundError -> suggest pip install <module>
    import_err_patterns = [
        r"ImportError:\s+No module named ['\"]([a-zA-Z0-9_\.]+)['\"]",
        r"ModuleNotFoundError:\s+No module named ['\"]([a-zA-Z0-9_\.]+)['\"]",
    ]
    for pat in import_err_patterns:
        m = re.search(pat, combined)
        if m:
            missing_mod = m.group(1)
            # safety: don't suggest installing stdlib names
            if missing_mod not in ("sys", "os", "subprocess", "typing"):
                return f"Missing module '{missing_mod}'. Try: pip install {missing_mod}  # then re-run firsttry"

    # 3. NameError -> ask to run pytest locally
    if "nameerror" in lower:
        return "Your code referenced something undefined (NameError). Run pytest locally, fix that symbol/import, then re-run firsttry."

    # 4. Pytest assertion failure -> instruct to run pytest
    if "pytest" in cmd_l and ("assertionerror" in lower or "assert " in lower):
        return "Tests are failing. Run pytest locally to reproduce, fix the failing test, then re-run firsttry."

    # 5. Lint / formatter quick fixes
    if "unused import" in lower or "f401" in lower:
        return "Ruff reports unused imports. Auto-fix with: ruff check . --fix"
    if "would reformat" in lower or "reformatted" in lower:
        return "Black formatting needed. Run: black ."

    # Generic fallback: none
    return None
