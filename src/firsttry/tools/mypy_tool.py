from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


class MypyTool:
    name = "mypy"
    phase = "slow"  # or "mutating" if you sequence it differently

    def __init__(self, repo_root: Path, targets: list[str] | None = None):
        self.repo_root = repo_root
        self.targets = targets or ["src"]

    def input_paths(self) -> list[str]:
        return [str(self.repo_root / t) for t in self.targets]

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

        # 2) Normal path with timeout protection
        from firsttry.utils.proc import run_cmd

        cmd_parts = ["mypy"] + self.targets
        cmd_str = " ".join(cmd_parts)

        try:
            exit_code, stdout, stderr = run_cmd(cmd_str)
        except FileNotFoundError:
            return "ok", {
                "stdout": "mypy not found; skipping (soft-skip)",
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
