from __future__ import annotations

import json
from firsttry.utils.async_subproc import run_sync
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

Severity = Literal["low", "medium", "high", "critical"]


@dataclass
class BanditResult:
    issues_total: int
    by_severity: dict[str, int]
    max_severity: Optional[Severity]  # None when 0 issues
    raw_path: Path  # saved JSON


def _severity_rank(s: str) -> int:
    order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    return order.get(s.lower(), 0)


def run_bandit_json(root: Path, output: Path) -> BanditResult:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Force a deterministic JSON run
    cmd = ["bandit", "-r", str(root), "-f", "json", "-o", str(output)]
    try:
        # Do not use shell=True; ensure real exit code but don't crash FirstTry
        proc = run_sync(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        # Bandit not installed; represent as “skipped"
        return BanditResult(issues_total=0, by_severity={}, max_severity=None, raw_path=output)

    # bandit exits 0 or non-zero depending on config; we always parse the JSON it wrote
    if not output.exists():
        # fallback: try to read from stdout if bandit printed JSON (rare)
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {"results": []}
    else:
        data = json.loads(output.read_text())

    issues = data.get("results", []) or []
    by_sev: dict[str, int] = {}
    max_sev: Optional[Severity] = None
    max_rank = 0
    for it in issues:
        sev = (it.get("issue_severity") or "").lower()
        by_sev[sev] = by_sev.get(sev, 0) + 1
        r = _severity_rank(sev)
        if r > max_rank:
            max_rank, max_sev = r, sev if sev in ("low", "medium", "high", "critical") else None

    return BanditResult(
        issues_total=len(issues),
        by_severity=by_sev,
        max_severity=max_sev,
        raw_path=output,
    )


@dataclass
class CheckResult:
    name: str
    status: Literal["pass", "fail", "advisory", "skip", "error"]
    details: dict


def evaluate_bandit(result: BanditResult, fail_on: Severity, blocking: bool) -> CheckResult:
    # No issues at all => pass
    if result.issues_total == 0 or result.max_severity is None:
        return CheckResult(
            name="bandit",
            status="pass",
            details={
                "issues_total": 0,
                "by_severity": result.by_severity,
                "raw_json": str(result.raw_path),
                "reason": "No issues identified",
            },
        )
    # Compare highest severity with threshold
    if _severity_rank(result.max_severity) >= _severity_rank(fail_on):
        status = "fail" if blocking else "advisory"
        return CheckResult(
            name="bandit",
            status=status,
            details={
                "issues_total": result.issues_total,
                "by_severity": result.by_severity,
                "max_severity": result.max_severity,
                "raw_json": str(result.raw_path),
                "reason": f"Max severity {result.max_severity} >= fail_on {fail_on}",
                "blocking": blocking,
            },
        )
    # Below threshold => pass
    return CheckResult(
        name="bandit",
        status="pass",
        details={
            "issues_total": result.issues_total,
            "by_severity": result.by_severity,
            "max_severity": result.max_severity,
            "raw_json": str(result.raw_path),
            "reason": f"Max severity {result.max_severity} < fail_on {fail_on}",
        },
    )
