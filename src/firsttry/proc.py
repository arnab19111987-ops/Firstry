"""Centralized, blocking subprocess helper.

Use this for one-shot external tool invocations so we consistently use
blocking subprocess.run (avoids asyncio finalizer races) and centralize
capture/output handling.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Sequence


def run_cmd(
    cmd: Sequence[str] | Iterable[str],
    cwd: Optional[Path | str] = None,
    env: Optional[dict] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    timeout: Optional[float] = None,
) -> subprocess.CompletedProcess:
    """Run a blocking command using subprocess.run and return the
    CompletedProcess object. This centralizes behavior so callers can
    rely on a stable surface (returncode, stdout, stderr).

    Parameters mirror subprocess.run's common arguments but keep the
    signature minimal for our needs.
    """

    # Normalize cwd to str when provided
    cwd_str = str(cwd) if cwd is not None else None

    # Decide stdout/stderr handling
    stdout_pipe = subprocess.PIPE if capture_output else None
    stderr_pipe = subprocess.PIPE if capture_output else None

    # Accept either a string command (shell-like) or a sequence of args.
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = list(cmd)

    return subprocess.run(
        args,
        cwd=cwd_str,
        env=env,
        stdout=stdout_pipe,
        stderr=stderr_pipe,
        text=text,
        check=check,
        timeout=timeout,
    )
