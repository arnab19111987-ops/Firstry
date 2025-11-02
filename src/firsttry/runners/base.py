# src/firsttry/runners/base.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RunnerResult:
    name: str
    ok: bool
    message: str
    tool: str
    code: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseRunner:
    tool: str = "base"

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> RunnerResult:  # pragma: no cover
        raise NotImplementedError

    async def run_cmd(
        self,
        name: str,
        tool: str,
        cmd: str,
        *,
        timeout: int = 60,
    ) -> RunnerResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return RunnerResult(
                name=name,
                ok=False,
                message=f"{tool} not found in PATH. Install it.",
                tool=tool,
                code="tool-not-found",
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            return RunnerResult(
                name=name,
                ok=False,
                message=f"{tool} timed out after {timeout}s",
                tool=tool,
                code="timeout",
            )

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        rc = proc.returncode
        ok = rc == 0
        msg = out or err or f"{tool} exited with code {rc}"
        return RunnerResult(name=name, ok=ok, message=msg, tool=tool)