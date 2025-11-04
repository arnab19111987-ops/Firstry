from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
from firsttry.proc import run_cmd
import os


class PytestTool:
    name = "pytest"
    phase = "slow"

    def __init__(self, repo_root: Path, extra_args: List[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def _tracked_test_files(self) -> List[str]:
        """
        Use Git to enumerate tracked test files and avoid directory recursion.
        Falls back to default dirs if not a Git repo or no tracked tests found.
        """
        try:
            from ..utils.git_cache import git_ls

            out_files = git_ls(self.repo_root, "tests")
            files = [
                ln for ln in out_files
                if ln.endswith(".py") and (
                    ln.rsplit("/", 1)[-1].startswith("test_") or ln.rsplit("/", 1)[-1].endswith("_test.py")
                )
            ]
            return files or []
        except Exception:
            return []

    def input_paths(self) -> List[str]:
        """
        Keep the orchestrator's pre-stat cheap by returning the exact files
        pytest will run. If none found, fall back to the prior directories.
        """
        files = self._tracked_test_files()
        if files:
            return files
        # Fall back to old behavior (keeps compatibility)
        return [str(self.repo_root / "src"), str(self.repo_root / "tests")]

    def run(self) -> Tuple[str, Dict[str, Any]]:
        # Prefer explicit file list to reduce pytest discovery overhead; fall back if empty.
        files = self._tracked_test_files()
        # Optional fast-fail mode for local dev (opt-in via env FT_FAST_FAIL=1)
        fast_fail_args: List[str] = []
        if os.environ.get("FT_FAST_FAIL") == "1":
            fast_fail_args = ["-q", "--maxfail=1", "-x"]

        cmd = ["pytest"] + fast_fail_args + self.extra_args + (files if files else [])

        try:
            proc = run_cmd(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return "fail", {
                "stdout": "",
                "stderr": "pytest executable not found in PATH. Hint: pip install pytest or run: make dev",
            }

        status = "ok" if proc.returncode == 0 else "fail"
        return status, {"stdout": proc.stdout, "stderr": proc.stderr}
