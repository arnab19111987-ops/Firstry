from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import subprocess
from .base import CheckRunner, RunResult, _hash_targets, _hash_config, ensure_bin
from ..twin.hashers import hash_bytes, tool_version_hash, env_fingerprint


class MypyRunner(CheckRunner):
    check_id = "mypy"

    def prereq_check(self) -> Optional[str]:
        return ensure_bin("mypy")

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str:
        tv = tool_version_hash(["mypy", "--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets)
        cfg = _hash_config(repo_root, ["mypy.ini", "pyproject.toml", "setup.cfg"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-mypy-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult:
        args = ["mypy", *targets, *flags] if targets else ["mypy", *flags]
        try:
            proc = subprocess.run(args, cwd=repo_root, text=True, capture_output=True, timeout=timeout_s)
            return RunResult(status="ok" if proc.returncode == 0 else "fail",
                             stdout=proc.stdout, stderr=proc.stderr)
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
