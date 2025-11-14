from __future__ import annotations

import subprocess
import time
from pathlib import Path

from ..utils.proc import to_str
from .base import CheckRunner
from .base import RunResult


class NpmLintRunner(CheckRunner):
    check_id = "npm-lint"

    def prereq_check(self) -> str | None:
        from shutil import which

        return None if which("npm") else "npm not found"

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        return "ft-v1-npm-lint-" + "0"

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        cmd = ["npm", "run", "lint", "--silent"]
        p = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout_s
        )
        dur = int((time.time() - t0) * 1000)
        return RunResult(
            name="npm-lint",
            rc=p.returncode,
            stdout=to_str(p.stdout),
            stderr=to_str(p.stderr),
            duration_ms=dur,
        )
