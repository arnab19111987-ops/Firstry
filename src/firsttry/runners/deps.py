# src/firsttry/runners/deps.py
from __future__ import annotations

import json
from typing import Any

from .base import BaseRunner, RunnerResult


class PipAuditRunner(BaseRunner):
    tool = "pip-audit"

    async def run(
        self,
        idx: int,
        ctx: dict[str, Any],
        item: dict[str, Any],
    ) -> RunnerResult:
        name = f"deps[{idx}]"
        cmd = item.get("cmd") or "pip-audit -f json"
        res = await self.run_cmd(name, "pip-audit", cmd)
        # even if nonzero, try to parse
        try:
            data = json.loads(res.message)
            vulns = data if isinstance(data, list) else []
            count = len(vulns)
            res.message = f"pip-audit: {count} vulnerable packages"
            res.extra["vulnerabilities"] = vulns
        except Exception:
            pass
        return res


class NpmAuditRunner(BaseRunner):
    tool = "npm-audit"

    async def run(
        self,
        idx: int,
        ctx: dict[str, Any],
        item: dict[str, Any],
    ) -> RunnerResult:
        name = f"deps-npm[{idx}]"
        cmd = item.get("cmd") or "npm audit --json"
        res = await self.run_cmd(name, "npm-audit", cmd)
        try:
            data = json.loads(res.message)
            vulns = data.get("vulnerabilities") or {}
            highs = sum(1 for v in vulns.values() if (v.get("severity") == "high"))
            critical = sum(1 for v in vulns.values() if (v.get("severity") == "critical"))
            moderate = sum(1 for v in vulns.values() if (v.get("severity") == "moderate"))
            low = sum(1 for v in vulns.values() if (v.get("severity") == "low"))
            res.message = (
                f"npm-audit: {critical} critical, {highs} high, {moderate} moderate, {low} low"
            )
            res.extra["vulnerabilities"] = vulns
        except Exception:
            # keep default message
            pass
        return res
