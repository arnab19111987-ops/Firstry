from __future__ import annotations

import asyncio
import subprocess
from typing import Optional


async def run(cmd: list[str], *, capture_output: bool = False, text: bool = False, **kw) -> subprocess.CompletedProcess:
    """Run a subprocess in an asyncio-safe fresh event loop context.

    Returns a subprocess.CompletedProcess similar to subprocess.run.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE if capture_output else None,
        stderr=asyncio.subprocess.PIPE if capture_output else None,
        **kw,
    )
    out, err = await proc.communicate()

    if text:
        if out is not None:
            try:
                out = out.decode("utf-8", errors="replace")
            except Exception:
                out = str(out)
        if err is not None:
            try:
                err = err.decode("utf-8", errors="replace")
            except Exception:
                err = str(err)

    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def run_sync(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Synchronous wrapper that runs the async helper in a fresh event loop.

    Use this from synchronous code paths to avoid leaking event loops at
    interpreter shutdown. Keep the signature small — we accept kwargs like
    capture_output=True, text=True, etc.
    """
    return asyncio.run(run(cmd, **kw))
