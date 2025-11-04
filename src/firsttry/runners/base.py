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
            # Use the centralized blocking helper executed in a thread so we
            # avoid creating asyncio subprocess transports that may outlive the
            # running loop. We still use the async semaphore to bound
            # concurrency.
            from firsttry.proc import run_cmd

            if sem is not None:
                if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                    ctx.setdefault("_active_concurrency", 0)
                    ctx.setdefault("_max_concurrency_seen", 0)

                async with sem:
                    if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                        ctx["_active_concurrency"] += 1
                        ctx["_max_concurrency_seen"] = max(ctx["_max_concurrency_seen"], ctx["_active_concurrency"])
                    try:
                        proc = await asyncio.to_thread(run_cmd, cmd, cwd=None, capture_output=True, text=True, timeout=timeout)
                    finally:
                        if ctx is not None and os.getenv("FT_DEBUG_CONCURRENCY") == "1":
                            ctx["_active_concurrency"] = max(0, ctx["_active_concurrency"] - 1)
                    out = proc.stdout or ""
                    err = proc.stderr or ""
                    rc = proc.returncode
                    ok = rc == 0
                    msg = (out.strip() if isinstance(out, str) else str(out)) or (err.strip() if isinstance(err, str) else str(err)) or f"{tool} exited with code {rc}"
                    return RunnerResult(name=name, ok=ok, message=msg, tool=tool)
            else:
                proc = await asyncio.to_thread(run_cmd, cmd, cwd=None, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            return RunnerResult(
                name=name,
                ok=False,
                message=f"{tool} not found in PATH. Install it.",
                tool=tool,
                code="tool-not-found",
            )

        # Interpret completed process
        rc = proc.returncode
        out = proc.stdout or ""
        err = proc.stderr or ""
        ok = rc == 0
        msg = (out.strip() if isinstance(out, str) else str(out)) or (err.strip() if isinstance(err, str) else str(err)) or f"{tool} exited with code {rc}"
        return RunnerResult(name=name, ok=ok, message=msg, tool=tool)