from __future__ import annotations

import subprocess
from pathlib import Path

from ..twin.hashers import env_fingerprint, hash_bytes, tool_version_hash
from ..utils.proc import to_str
from .base import CheckRunner, RunResult, ensure_bin, hash_config, hash_targets


class RuffRunner(CheckRunner):
    check_id = "ruff"

    def prereq_check(self) -> str | None:
        return ensure_bin("ruff")

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str:
        tv = tool_version_hash(["ruff", "--version"])
        env = env_fingerprint()
        tgt = hash_targets(repo_root, targets)
        cfg = hash_config(repo_root, ["pyproject.toml", ".ruff.toml", "ruff.toml"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-ruff-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = __import__("time").time()
        cmd = ["ruff", "check"]
        if files:
            cmd += files
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(repo_root),
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            dur = int((__import__("time").time() - t0) * 1000)
            return RunResult(
                name="ruff",
                rc=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                duration_ms=dur,
            )
        except subprocess.TimeoutExpired as e:
            return RunResult(name="ruff", rc=2, stdout=to_str(e.stdout), stderr=str(e))
