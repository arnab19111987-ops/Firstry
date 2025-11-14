# src/firsttry/runners/js.py
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from ..twin.hashers import hash_bytes
from ..utils.proc import to_str
from .base import CheckRunner
from .base import RunResult

_ESLINT_RULE_RE = re.compile(r"\(([^()]+)\)\s*$")


class ESLintRunner(CheckRunner):
    check_id = "eslint"

    def prereq_check(self) -> str | None:
        # prefer local npx-based eslint or global eslint
        from shutil import which

        if which("npx") or which("eslint"):
            return None
        return "eslint (or npx) not found"

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        # best-effort: include intent only
        return "ft-v1-eslint-" + hash_bytes(b"")

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        cmd = ["npx", "-y", "eslint", "-f", "unix"]
        if files:
            cmd += files
        else:
            cmd += ["."]
        p = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout_s
        )
        dur = int((time.time() - t0) * 1000)
        # parse message code if present
        msg = to_str(p.stdout) or to_str(p.stderr)
        code = ""
        m = _ESLINT_RULE_RE.search(msg)
        if m:
            code = m.group(1)
        return RunResult(
            name="eslint",
            rc=p.returncode,
            stdout=to_str(p.stdout),
            stderr=to_str(p.stderr),
            duration_ms=dur,
            code=code,
        )


class NpmTestRunner(CheckRunner):
    check_id = "npm-test"

    def prereq_check(self) -> str | None:
        from shutil import which

        return None if which("npm") else "npm not found"

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        return "ft-v1-npmtest-" + hash_bytes(b"")

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        cmd = ["npm", "test"]
        p = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout_s
        )
        dur = int((time.time() - t0) * 1000)
        return RunResult(
            name="npm-test",
            rc=p.returncode,
            stdout=to_str(p.stdout),
            stderr=to_str(p.stderr),
            duration_ms=dur,
        )
