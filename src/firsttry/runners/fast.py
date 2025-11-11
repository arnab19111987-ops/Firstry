"""Fast/Lite tier runner with lazy imports for minimal overhead."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def run(args: argparse.Namespace) -> int:
    """Run fast/free-lite tier checks (ruff only).

    Lazy imports ensure we only load what we need at call time.
    """
    # Set no-ui mode if requested
    if getattr(args, "no_ui", False):
        from firsttry.reports.ui import set_no_ui

        set_no_ui(True)

    # Lazy import at call site to avoid loading heavy dependencies
    from pathlib import Path

    from firsttry.tools.ruff_tool import RuffTool

    repo_root = Path.cwd()

    # Create and run ruff tool with changed-only mode for fast tier
    # This auto-detects changed files via git diff for sub-second feedback
    changed_only = getattr(args, "changed_only", True)  # Default True for fast tier
    tool = RuffTool(repo_root, extra_args=[], changed_only=changed_only)

    status, _details = tool.run()

    if status == "ok":
        return 0
    return 1
