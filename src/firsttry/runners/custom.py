# src/firsttry/runners/custom.py
from __future__ import annotations

from typing import Any, Dict

from .base import BaseRunner, RunnerResult


class CustomRunner(BaseRunner):
    tool = "custom"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:
        display_name = item.get("tool") or item.get("name") or "custom"
        name = f"{display_name}[{idx}]"
        cmd = item.get("cmd")
        if not cmd:
            return RunnerResult(name=name, ok=True, message="no cmd", tool=display_name)
        return await self.run_cmd(name, display_name, cmd, ctx=ctx)