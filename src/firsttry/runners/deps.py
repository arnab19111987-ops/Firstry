# src/firsttry/runners/deps.py
from __future__ import annotations

import json
from typing import Any, Dict, TYPE_CHECKING

from .base import BaseRunner, RunnerResult


class PipAuditRunner(BaseRunner):
    tool = "pip-audit"

    async def run(
        self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]
    ) -> RunnerResult:
        name = f"deps[{idx}]"
        cmd = item.get("cmd") or "pip-audit -f json"
        res = await self.run_cmd(name, "pip-audit", cmd)
        # even if nonzero, try to parse
        try:
            if res.message:
                data = json.loads(res.message)
                vulns = data if isinstance(data, list) else []
                count = len(vulns)
                res.message = f"pip-audit: {count} vulnerable packages"
                if res.extra is None:
                    res.extra = {}
                if isinstance(res.extra, dict):
                    res.extra["vulnerabilities"] = vulns
        except Exception:
            pass
        return res

    if TYPE_CHECKING:  # pragma: no cover - static typing aid only

        async def run_cmd(self, name: str, tool: str, cmd: Any) -> RunnerResult: ...


class NpmAuditRunner(BaseRunner):
    tool = "npm-audit"

    async def run(
        self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]
    ) -> RunnerResult:
        name = f"deps-npm[{idx}]"
        cmd = item.get("cmd") or "npm audit --json"
        res = await self.run_cmd(name, "npm-audit", cmd)
        try:
            if res.message:
                data = json.loads(res.message)
                vulns = data.get("vulnerabilities") or {}
                highs = sum(1 for v in vulns.values() if (v.get("severity") == "high"))
                critical = sum(
                    1 for v in vulns.values() if (v.get("severity") == "critical")
                )
                moderate = sum(
                    1 for v in vulns.values() if (v.get("severity") == "moderate")
                )
                low = sum(1 for v in vulns.values() if (v.get("severity") == "low"))
                res.message = f"npm-audit: {critical} critical, {highs} high, {moderate} moderate, {low} low"
                if res.extra is None:
                    res.extra = {}
                if isinstance(res.extra, dict):
                    res.extra["vulnerabilities"] = vulns
        except Exception:
            # keep default message
            pass
        return res

    if TYPE_CHECKING:  # pragma: no cover - static typing aid only

        async def run_cmd(self, name: str, tool: str, cmd: Any) -> RunnerResult: ...
