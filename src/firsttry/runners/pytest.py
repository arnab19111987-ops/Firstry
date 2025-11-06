from __future__ import annotations

import subprocess
from pathlib import Path

from ..twin.hashers import env_fingerprint
from ..twin.hashers import hash_bytes
from ..twin.hashers import tool_version_hash
from .base import CheckRunner
from .base import RunResult
from .base import _hash_config
from .base import _hash_targets
from .base import ensure_bin


class PytestRunner(CheckRunner):
    check_id = "pytest"

    def prereq_check(self) -> str | None:
        return ensure_bin("pytest")

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str:
        tv = tool_version_hash(["pytest", "--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["tests"])
        cfg = _hash_config(
            repo_root,
            ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"],
        )
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-pytest-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
        *,
        timeout_s: int,
    ) -> RunResult:
        test_targets = targets or ["tests"]
        args = ["pytest", "-q", *test_targets, *flags]
        try:
            proc = subprocess.run(
                args,
                cwd=repo_root,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            return RunResult(
                status="ok" if proc.returncode == 0 else "fail",
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
