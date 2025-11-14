"""Process execution utilities with timeout and safe I/O handling."""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import Tuple
from typing import Union

DEFAULT_TIMEOUT = int(os.getenv("FT_TOOL_TIMEOUT_SEC", "30"))


def _to_str(x: Union[bytes, str, None]) -> str:
    """Convert bytes, str, or None to str for type safety."""
    if x is None:
        return ""
    if isinstance(x, (bytes, bytearray, memoryview)):
        try:
            return bytes(x).decode("utf-8", errors="replace")
        except Exception:
            return str(x)
    if isinstance(x, str):
        return x
    # Fallback: coerce to str
    return str(x)


def to_str(x: Union[bytes, str, None]) -> str:
    """Public wrapper for converting bytes/None to str.

    Some modules used in the project previously imported the private
    `_to_str`. Expose a stable public `to_str` helper and keep `_to_str`
    for backward compatibility.
    """
    return _to_str(x)


def run_cmd(cmd: str, timeout: int | None = None) -> Tuple[int, str, str]:
    """
    Run a shell command safely:
    - Non-interactive (stdin=DEVNULL)
    - Captures stdout/stderr
    - Enforces timeout

    Args:
        cmd: Command string to execute
        timeout: Timeout in seconds (default: DEFAULT_TIMEOUT)

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    to = timeout or DEFAULT_TIMEOUT
    try:
        cp = subprocess.run(
            cmd if isinstance(cmd, list) else shlex.split(cmd),
            check=False,
            capture_output=True,
            text=True,
            timeout=to,
            stdin=subprocess.DEVNULL,
        )
        return cp.returncode, _to_str(cp.stdout), _to_str(cp.stderr)
    except subprocess.TimeoutExpired as e:
        return 124, _to_str(e.stdout), _to_str(e.stderr)  # 124 = timeout
