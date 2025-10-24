from __future__ import annotations

from typing import List


def run_pre_commit_gate() -> List[str]:
    """Return a list of shell commands that represent the pre-commit gate.
    This is a placeholder used by the CLI. Real implementation lives in tools/firsttry.
    """
    return [
        "ruff check .",
        "python -m mypy .",
        "python -m pytest -q",
    ]
