from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import shutil, subprocess
from .base import CheckRunner, RunResult, ensure_bin, _hash_targets, _hash_config
from ..twin.hashers import hash_bytes, tool_version_hash, env_fingerprint

class NpmLintRunner(CheckRunner):
    check_id = "npm-lint"

    def prereq_check(self) -> Optional[str]:
        # ok if either eslint or npx (for local eslint) is available
        if shutil.which("eslint") or shutil.which("npx"):
            return None
        return "eslint (or npx) not found. Install eslint (devDependency) or ensure npx is available."

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str:
        ev = tool_version_hash(["npx","eslint","--version"]) if shutil.which("npx") else tool_version_hash(["eslint","--version"]) if shutil.which("eslint") else hash_bytes(b"")
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["."])
        cfg = _hash_config(repo_root, ["package.json",".eslintrc",".eslintrc.js",".eslintrc.cjs","package-lock.json","pnpm-lock.yaml","yarn.lock"])
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-eslint-" + hash_bytes(f"{ev}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult:
        args = ["npx","eslint","--no-color", * (targets or ["."]), *flags] if shutil.which("npx") else ["eslint","--no-color", * (targets or ["."]), *flags]
        try:
            p = subprocess.run(args, cwd=repo_root, text=True, capture_output=True, timeout=timeout_s)
            return RunResult(status="ok" if p.returncode == 0 else "fail", stdout=p.stdout, stderr=p.stderr)
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
