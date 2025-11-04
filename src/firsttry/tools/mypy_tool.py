from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
from firsttry.proc import run_cmd
from ..utils.git_cache import git_ls


class MypyTool:
    name = "mypy"
    phase = "slow"  # or "mutating" if you sequence it differently

    def __init__(self, repo_root: Path, targets: List[str] | None = None):
        self.repo_root = repo_root
        # keep existing behavior if caller passed explicit targets
        self.targets = targets or ["src", "tests"]

    def _tracked_py_files(self) -> List[str]:
        """
        Prefer exact, git-tracked Python files to avoid directory walks.
        Gracefully fall back to the provided directory targets when not a git repo.
        """
        try:
            files = git_ls(self.repo_root, "*.py")
            return files or self.targets
        except Exception:
            return self.targets

    def input_paths(self) -> List[str]:
        # Return exactly what we’ll pass to mypy so any pre-stat stays O(files).
        return self._tracked_py_files()

    def run(self) -> Tuple[str, Dict[str, Any]]:
        files = self._tracked_py_files()

        # Keep cache usage (default .mypy_cache). Do NOT delete caches elsewhere.
        cmd = ["mypy"] + files
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
                "stderr": "mypy executable not found in PATH. Hint: pip install mypy or run: make dev",
            }

        status = "ok" if proc.returncode == 0 else "fail"
        return status, {"stdout": proc.stdout, "stderr": proc.stderr}
