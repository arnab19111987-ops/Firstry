from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import subprocess
from .base import CheckRunner, RunResult, _hash_targets, _hash_config, ensure_bin
from ..twin.hashers import hash_bytes, tool_version_hash, env_fingerprint


class PytestRunner(CheckRunner):
    check_id = "pytest"

    def prereq_check(self) -> Optional[str]:
        return ensure_bin("pytest")

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str:
        tv = tool_version_hash(["pytest", "--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["tests"])
        cfg = _hash_config(repo_root, ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-pytest-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult:
        test_targets = targets or ["tests"]
        args = ["pytest", "-q", *test_targets, *flags]
        try:
            proc = subprocess.run(args, cwd=repo_root, text=True, capture_output=True, timeout=timeout_s)
            return RunResult(status="ok" if proc.returncode == 0 else "fail",
                             stdout=proc.stdout, stderr=proc.stderr)
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
