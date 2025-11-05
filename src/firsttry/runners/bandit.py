from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import subprocess
from .base import CheckRunner, RunResult, ensure_bin, _hash_targets, _hash_config
from ..twin.hashers import hash_bytes, tool_version_hash, env_fingerprint

class BanditRunner(CheckRunner):
    check_id = "bandit"

    def prereq_check(self) -> Optional[str]:
        return ensure_bin("bandit")

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str:
        tv = tool_version_hash(["bandit","--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["."])
        cfg = _hash_config(repo_root, ["pyproject.toml","bandit.yml","bandit.yaml"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-bandit-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult:
        args = ["bandit","-q","-r", * (targets or ["."]), *flags]
        try:
            p = subprocess.run(args, cwd=repo_root, text=True, capture_output=True, timeout=timeout_s)
            return RunResult(status="ok" if p.returncode == 0 else "fail", stdout=p.stdout, stderr=p.stderr)
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
