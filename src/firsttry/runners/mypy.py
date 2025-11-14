from __future__ import annotations

import subprocess
import time
from pathlib import Path

from ..twin.hashers import env_fingerprint
from ..twin.hashers import hash_bytes
from ..twin.hashers import tool_version_hash
from ..utils.proc import to_str
from .base import CheckRunner
from .base import RunResult
from .base import ensure_bin
from .base import hash_config
from .base import hash_targets


class MypyRunner(CheckRunner):
    check_id = "mypy"

    def prereq_check(self) -> str | None:
        return ensure_bin("mypy")

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str:
        tv = tool_version_hash(["mypy", "--version"])
        env = env_fingerprint()
        tgt = hash_targets(repo_root, targets or ["."])
        cfg = hash_config(repo_root, ["mypy.ini", "pyproject.toml", "setup.cfg"])
        intent = hash_bytes((" ".join(sorted(flags or []))).encode())
        return "ft-v1-mypy-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        if files:
            args = ["mypy", *files]
        else:
            args = ["mypy"]
        try:
            proc = subprocess.run(
                args,
                cwd=str(repo_root),
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            dur = int((time.time() - t0) * 1000)
            return RunResult(
                name="mypy",
                rc=proc.returncode,
                stdout=to_str(proc.stdout),
                stderr=to_str(proc.stderr),
                duration_ms=dur,
            )
        except subprocess.TimeoutExpired as e:
            dur = int((time.time() - t0) * 1000)
            return RunResult(
                name="mypy",
                rc=124,
                stdout=to_str(getattr(e, "stdout", "")),
                stderr=str(e),
                duration_ms=dur,
            )
