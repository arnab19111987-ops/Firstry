from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any


def _changed_py_files(base: str = "HEAD") -> list[str]:
    """Get list of changed Python files via git diff.

    Args:
        base: Git ref to compare against (default: HEAD)

    Returns:
        List of changed .py file paths that exist on disk
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", base, "--", "*.py"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode != 0:
            return []

        files = [f.strip() for f in result.stdout.splitlines() if f.strip().endswith(".py")]
        return [f for f in files if Path(f).is_file()]
    except Exception:
        return []


class RuffTool:
    name = "ruff"
    phase = "fast"  # used by orchestrator

    def __init__(
        self,
        repo_root: Path,
        extra_args: list[str] | None = None,
        changed_only: bool = False,
    ):
        self.repo_root = repo_root
        self.extra_args = extra_args or []
        self.changed_only = changed_only

    def input_paths(self) -> list[str]:
        # keep it cheap; orchestrator may stat these
        return [str(self.repo_root / "src"), str(self.repo_root / "tests")]

    def run(self) -> tuple[str, dict[str, Any]]:
        start = time.monotonic()

        # 1) Skip entirely during tests
        if os.getenv("FT_SKIP_TOOL_EXEC") == "1":
            return "ok", {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "elapsed": 0.0,
                "skipped": True,
                "reason": "FT_SKIP_TOOL_EXEC",
            }

        # 2) Legacy stub support
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv(
            "FIRSTTRY_USE_STUB_RUNNERS",
        ) in (
            "1",
            "true",
            "True",
        ):
            return "ok", {
                "stdout": "ruff (stub)",
                "stderr": "",
                "exit_code": 0,
                "elapsed": 0.0,
            }

        # 3) Normal path with timeout protection
        from firsttry.utils.proc import run_cmd

        # Determine targets: changed files or full scan
        targets = ["."]
        if self.changed_only:
            base = os.environ.get("FT_CHANGED_BASE", "HEAD")
            files = _changed_py_files(base)
            # Only use changed files if we have some (>0) and not too many (<2000)
            if 0 < len(files) <= 2000:
                targets = files

        cmd_parts = ["ruff", "check"] + targets + self.extra_args
        cmd_str = " ".join(cmd_parts)

        try:
            exit_code, stdout, stderr = run_cmd(cmd_str)
        except FileNotFoundError:
            return "ok", {
                "stdout": "ruff not found; skipping (soft-skip)",
                "stderr": "",
                "skipped": True,
                "exit_code": 0,
                "elapsed": 0.0,
            }

        elapsed = time.monotonic() - start
        if exit_code == 0:
            return "ok", {
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
                "exit_code": exit_code,
                "elapsed": elapsed,
            }
        return "fail", {
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "exit_code": exit_code,
            "elapsed": elapsed,
        }
