# src/firsttry/runners/js.py
from __future__ import annotations

import re
from typing import Any, Dict

from .base import BaseRunner, RunnerResult

_ESLINT_RULE_RE = re.compile(r"\(([^()]+)\)\s*$")


class ESLintRunner(BaseRunner):
    tool = "eslint"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"lint-js[{idx}]"
        cmd = item.get("cmd") or "npx eslint ."
        res = await self.run_cmd(name, "eslint", cmd, ctx=ctx)
        if not res.ok:
            m = _ESLINT_RULE_RE.search(res.message)
            if m:
                res.code = m.group(1)
        return res


class NpmTestRunner(BaseRunner):
    tool = "npm-test"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        name = f"tests-js[{idx}]"
        cmd = item.get("cmd") or "npm test"
        return await self.run_cmd(name, "npm-test", cmd, ctx=ctx)