# src/firsttry/runners/deps.py
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any
from typing import cast

from ..twin.hashers import hash_bytes
from ..utils.proc import to_str
from .base import CheckRunner
from .base import RunResult


class PipAuditRunner(CheckRunner):
    check_id = "pip-audit"

    def prereq_check(self) -> str | None:
        from shutil import which

        return None if which("pip-audit") else "pip-audit not found"

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        return "ft-v1-pip-audit-" + hash_bytes(b"")

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        cmd = ["pip-audit", "-f", "json"]
        if files:
            for f in files:
                cmd += ["-r", f]
        p = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout_s
        )
        dur = int((time.time() - t0) * 1000)
        # attempt to parse JSON for richer message
        try:
            data = json.loads(p.stdout or "{}")
            if isinstance(data, list):
                vulns = cast(list[dict[str, Any]], data)
            else:
                vulns = []
            count = len(vulns)
            extra: dict[str, Any] = {"vulnerabilities": vulns}
            return RunResult(
                name="pip-audit",
                rc=p.returncode,
                stdout=to_str(p.stdout),
                stderr=to_str(p.stderr),
                duration_ms=dur,
                extra=extra,
                message=f"pip-audit: {count} vulnerable packages",
            )
        except Exception:
            return RunResult(
                name="pip-audit",
                rc=p.returncode,
                stdout=to_str(p.stdout),
                stderr=to_str(p.stderr),
                duration_ms=dur,
            )


class NpmAuditRunner(CheckRunner):
    check_id = "npm-audit"

    def prereq_check(self) -> str | None:
        from shutil import which

        return None if which("npm") else "npm not found"

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        return "ft-v1-npm-audit-" + hash_bytes(b"")

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        t0 = time.time()
        cmd = ["npm", "audit", "--json"]
        p = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout_s
        )
        dur = int((time.time() - t0) * 1000)
        try:
            data = json.loads(p.stdout or "{}")
            raw_v: Any = data.get("vulnerabilities") or {}
            if isinstance(raw_v, dict):
                vulns = cast(dict[str, Any], raw_v)
            else:
                vulns = {}
            highs = sum(
                1
                for v in vulns.values()
                if (isinstance(v, dict) and cast(dict[str, Any], v).get("severity") == "high")
            )
            critical = sum(
                1
                for v in vulns.values()
                if (isinstance(v, dict) and cast(dict[str, Any], v).get("severity") == "critical")
            )
            moderate = sum(
                1
                for v in vulns.values()
                if (isinstance(v, dict) and cast(dict[str, Any], v).get("severity") == "moderate")
            )
            low = sum(
                1
                for v in vulns.values()
                if (isinstance(v, dict) and cast(dict[str, Any], v).get("severity") == "low")
            )
            extra: dict[str, Any] = {"vulnerabilities": vulns}
            msg = f"npm-audit: {critical} critical, {highs} high, {moderate} moderate, {low} low"
            return RunResult(
                name="npm-audit",
                rc=p.returncode,
                stdout=to_str(p.stdout),
                stderr=to_str(p.stderr),
                duration_ms=dur,
                extra=extra,
                message=msg,
            )
        except Exception:
            return RunResult(
                name="npm-audit",
                rc=p.returncode,
                stdout=to_str(p.stdout),
                stderr=to_str(p.stderr),
                duration_ms=dur,
            )
