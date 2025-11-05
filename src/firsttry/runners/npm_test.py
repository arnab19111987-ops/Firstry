from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import subprocess
from .base import CheckRunner, RunResult, ensure_bin, _hash_targets, _hash_config
from ..twin.hashers import hash_bytes, tool_version_hash, env_fingerprint

class NpmTestRunner(CheckRunner):
    check_id = "npm-test"

    def prereq_check(self) -> Optional[str]:
        return ensure_bin("npm")

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str:
        nv = tool_version_hash(["node","--version"])
        pv = tool_version_hash(["npm","--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["."])
        cfg = _hash_config(repo_root, ["package.json","package-lock.json","pnpm-lock.yaml","yarn.lock"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-npmtest-" + hash_bytes(f"{nv}|{pv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult:
        # Run once per target that has package.json; else repo root
        targets = targets or ["."]
        pkgs = [repo_root / t for t in targets if (repo_root / t / "package.json").exists()] or [repo_root]
        out, err, rc = "", "", 0
        for pth in pkgs:
            p = subprocess.run(
                ["npm", "test", "--silent", "--", *flags],
                cwd=pth,
                text=True,
                capture_output=True,
                timeout=timeout_s,
            )
            out += p.stdout
            err += p.stderr
            rc |= p.returncode
        return RunResult(status="ok" if rc == 0 else "fail", stdout=out, stderr=err)
