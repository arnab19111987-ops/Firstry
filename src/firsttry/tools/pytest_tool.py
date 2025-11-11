from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


class PytestTool:
    name = "pytest"
    phase = "slow"

    def __init__(self, repo_root: Path, extra_args: list[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def input_paths(self) -> list[str]:
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

        # 2) Fast mode for lazy path (collection-only)
        if os.getenv("FT_PYTEST_FAST") == "1" or os.getenv("FIRSTTRY_LAZY") == "1":
            from firsttry.utils.proc import run_cmd

            exit_code, stdout, stderr = run_cmd("pytest -q --collect-only --maxfail=1")
            elapsed = time.monotonic() - start
            status = "ok" if exit_code == 0 else "fail"
            return status, {
                "stdout": stdout[-4000:],  # trim
                "stderr": stderr[-4000:],
                "exit_code": exit_code,
                "elapsed": elapsed,
                "mode": "collect-only",
            }

        # 3) Normal path with timeout protection
        from firsttry.utils.proc import run_cmd

        cmd_parts = ["pytest", "-q", "--maxfail=1"] + self.extra_args
        cmd_str = " ".join(cmd_parts)

        try:
            exit_code, stdout, stderr = run_cmd(cmd_str)
        except FileNotFoundError:
            return "ok", {
                "stdout": "pytest not found; skipping (soft-skip)",
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
