"""Strict/Free-Strict tier runner with lazy imports for minimal overhead."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def run(args: argparse.Namespace) -> int:
    """Run strict/free-strict tier checks (ruff + mypy + pytest).

    Lazy imports ensure we only load what we need at call time.
    """
    # Set no-ui mode if requested
    if getattr(args, "no_ui", False):
        from firsttry.reports.ui import set_no_ui

        set_no_ui(True)

    from pathlib import Path

    repo_root = Path.cwd()
    rc = 0

    # Lazy import ruff at call site
    from firsttry.tools.ruff_tool import RuffTool

    ruff_tool = RuffTool(repo_root, extra_args=[])
    status, _ = ruff_tool.run()
    if status != "ok":
        rc = 1

    # Lazy import mypy at call site (uses targets, not extra_args)
    from firsttry.tools.mypy_tool import MypyTool

    mypy_tool = MypyTool(repo_root, targets=["src"])
    status, _ = mypy_tool.run()
    if status != "ok":
        rc = 1

    # Lazy import pytest at call site
    from firsttry.tools.pytest_tool import PytestTool

    pytest_tool = PytestTool(repo_root, extra_args=["-x", "--tb=no", "-q"])
    status, _ = pytest_tool.run()
    if status != "ok":
        rc = 1

    return rc
