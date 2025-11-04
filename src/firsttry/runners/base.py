# src/firsttry/runners/base.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import threading
import os
from typing import Any, Dict


@dataclass
class RunnerResult:
    name: str
    ok: bool
    message: str
    tool: str
    code: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


# Global sync semaphore exposed for sync helpers (scanner) to respect the same
# concurrency ceiling as the async orchestrator. Will be set by the orchestrator.
GLOBAL_SYNC_SEMAPHORE: threading.Semaphore | None = None


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
        ctx: Dict[str, Any] | None = None,
        semaphore: Any | None = None,
    ) -> RunnerResult:
        # Determine semaphore: explicit kw wins, then ctx-provided global semaphore
        sem = semaphore if semaphore is not None else (ctx or {}).get("global_semaphore") if ctx else None

        try:
            # If a semaphore is present, use it to bound concurrency for subprocesses
            if sem is not None:
                # best-effort bookkeeping: track active and max concurrent acquisitions on ctx
                if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                    ctx.setdefault("_active_concurrency", 0)
                    ctx.setdefault("_max_concurrency_seen", 0)

                async with sem:
                    # update active counter after acquiring semaphore
                    if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                        ctx["_active_concurrency"] += 1
                        ctx["_max_concurrency_seen"] = max(ctx["_max_concurrency_seen"], ctx["_active_concurrency"])

                    proc = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    # once the subprocess is created we will wait for it; decrement active counter when done
                    try:
                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                    finally:
                        if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                            ctx["_active_concurrency"] = max(0, ctx["_active_concurrency"] - 1)

                        # reuse captured stdout/stderr handling below
                        out = stdout.decode().strip() if stdout is not None else ""
                        err = stderr.decode().strip() if stderr is not None else ""
                        rc = proc.returncode
                        ok = rc == 0
                        msg = out or err or f"{tool} exited with code {rc}"
                        return RunnerResult(name=name, ok=ok, message=msg, tool=tool)
            else:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # no semaphore bookkeeping; fall through to normal communicate
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