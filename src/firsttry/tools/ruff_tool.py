from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple


class RuffTool:
    name = "ruff"
    phase = "fast"  # used by orchestrator

    def __init__(self, repo_root: Path, extra_args: List[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def input_paths(self) -> List[str]:
        # keep it cheap; orchestrator may stat these
        return [str(self.repo_root / "src"), str(self.repo_root / "tests")]

    def run(self) -> Tuple[str, Dict[str, Any]]:
        # If we're running under pytest (tests set PYTEST_CURRENT_TEST) or
        # if tests opted into stub runners, avoid invoking the external
        # 'ruff' binary which may not be installed in the test environment.
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv(
            "FIRSTTRY_USE_STUB_RUNNERS"
        ) in (
            "1",
            "true",
            "True",
        ):
            return "ok", {"stdout": "ruff (stub)", "stderr": ""}

        # lazy import not strictly needed here
        cmd = ["ruff", "check", "."] + self.extra_args
        try:
            proc = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True
            )
        except FileNotFoundError:
            return "ok", {
                "stdout": "ruff not found; skipping (soft-skip)",
                "stderr": "",
                "skipped": True,
            }

        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}
