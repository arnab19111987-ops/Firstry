# src/firsttry/runners/custom.py
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from .base import BaseRunner, RunnerResult


class CustomRunner(BaseRunner):
    tool = "custom"

    # Minimal attributes + helpers to satisfy the CheckRunner protocol
    check_id = "custom"

    def build_cache_key(self, repo_root, targets, flags):
        return ""

    def prereq_check(self):
        return None

    async def run(
        self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]
    ) -> RunnerResult:
        display_name = item.get("tool") or item.get("name") or "custom"
        name = f"{display_name}[{idx}]"
        cmd = item.get("cmd")
        if not cmd:
            return RunnerResult(name=name, ok=True, message="no cmd", tool=display_name)
        return await self.run_cmd(name, display_name, cmd)

    if TYPE_CHECKING:  # pragma: no cover - static typing aid only

        async def run_cmd(self, name: str, tool: str, cmd: Any) -> RunnerResult: ...
