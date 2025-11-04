from __future__ import annotations

from firsttry.proc import run_cmd
from ..utils.git_cache import git_ls
from pathlib import Path
from typing import Dict, Any, List, Tuple


class RuffTool:
    name = "ruff"
    phase = "fast"  # used by orchestrator

    def __init__(self, repo_root: Path, extra_args: List[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def _tracked_py_files(self) -> List[str]:
        """
        Use Git to get the exact Python files to check.
        This avoids any repo-wide directory walk and respects .gitignore.
        """
        try:
            files = git_ls(self.repo_root, "*.py")
            return files or ["src", "tests"]
        except Exception:
            return ["src", "tests"]

    def input_paths(self) -> List[str]:
        """
        Keep this cheap: return the exact files Ruff will receive.
        If your orchestrator stats these, it stays O(files) without recursing directories.
        """
        return self._tracked_py_files()

    def run(self) -> Tuple[str, Dict[str, Any]]:
        # Build the command with force-exclude to ensure Ruff doesn't re-enter ignored dirs.
        files = self._tracked_py_files()
        cmd = ["ruff", "check", "--force-exclude"] + self.extra_args + files

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
                "stderr": "ruff executable not found in PATH. Hint: pip install ruff or run: make dev",
            }

        status = "ok" if proc.returncode == 0 else "fail"
        return status, {"stdout": proc.stdout, "stderr": proc.stderr}
