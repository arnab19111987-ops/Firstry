from __future__ import annotations

import subprocess
from pathlib import Path

from ..twin.hashers import env_fingerprint, hash_bytes, tool_version_hash
from .base import CheckRunner, RunResult, ensure_bin, hash_config, hash_targets


class NpmTestRunner(CheckRunner):
    check_id = "npm-test"

    def prereq_check(self) -> str | None:
        return ensure_bin("npm")

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        nv = tool_version_hash(["node", "--version"])
        pv = tool_version_hash(["npm", "--version"])
        env = env_fingerprint()
        tgt = hash_targets(repo_root, targets or ["."])
        cfg = hash_config(
            repo_root,
            ["package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"],
        )
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-npmtest-" + hash_bytes(f"{nv}|{pv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        # Run npm test once per package that has package.json; else repo root
        targets = files or ["."]
        pkgs = [repo_root / t for t in targets if (repo_root / t / "package.json").exists()] or [
            repo_root,
        ]
        out, err, rc = "", "", 0
        for pth in pkgs:
            p = subprocess.run(
                ["npm", "test", "--silent"],
                cwd=str(pth),
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
            out += p.stdout or ""
            err += p.stderr or ""
            rc |= p.returncode
        return RunResult(name="npm-test", rc=rc, stdout=out, stderr=err, duration_ms=0)
