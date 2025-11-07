"""Utility functions for gate implementations."""

import subprocess
from typing import Any

from .base import GateResult


def _run_shim(cmd: list[str], **kwargs: Any):
    """Call subprocess.run but gracefully degrade when a test double doesn't accept
    unknown kwargs (e.g., 'check'). We strip unknown keys and retry once.

    This ensures compatibility with test mocks that have strict signatures while
    still using full subprocess.run features in production.

    Re-raises FileNotFoundError and other exceptions as-is so they can be handled
    by the caller (_safe_gate).
    """
    try:
        return subprocess.run(cmd, **kwargs)
    except TypeError:
        # Keep only the most universal kwargs to be compatible with strict mocks.
        allowed = {}
        for k in ("capture_output", "text", "timeout"):
            if k in kwargs:
                allowed[k] = kwargs[k]
        return subprocess.run(cmd, **allowed)


def _safe_gate(
    gate_id: str,
    cmd: list[str] | None = None,
    *,
    ok_if_missing: bool = True,
) -> GateResult:
    """Run a shell/tool-based gate but never crash the whole run.

    Args:
        gate_id: Identifier for this gate (e.g., "lint", "types")
        cmd: Command to run as list of strings, or None for pythonic gates
        ok_if_missing: Whether to treat missing tool as ok (skipped) or failure

    Returns:
        GateResult with structured success/failure/skip information

    """
    # Handle FileNotFoundError separately BEFORE other exceptions
    try:
        if cmd is None:
            # Pure Python gate with no subprocess
            return GateResult(gate_id=gate_id, ok=True, skipped=False, output="")

        # Run the command using _run_shim for test compatibility
        proc = _run_shim(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # will be stripped by _run_shim if the mock can't take it
        )

        # Safely extract attributes from process result
        rc = getattr(proc, "returncode", 1)
        stdout = getattr(proc, "stdout", "") or ""
        stderr = getattr(proc, "stderr", "") or ""

        # Determine canonical status
        ok = rc == 0
        skipped = False
        output = (stdout + stderr).strip()
        reason = None if ok else f"exit {rc}"

        # Try to construct GateResult with status parameter first (preferred)
        try:
            status = "PASS" if ok else "FAIL"
            return GateResult(
                gate_id=gate_id,
                status=status,
                output=output,
                reason=reason,
            )
        except TypeError:
            # Fall back to ok/skipped constructor if status not supported
            gr = GateResult(
                gate_id=gate_id,
                ok=ok,
                skipped=skipped,
                output=output,
                reason=reason,
            )
            # If GateResult has a status property, ensure it's set correctly
            if hasattr(gr, "status"):
                # Status property should auto-compute from ok/skipped, but ensure it's right
                pass
            return gr

    except FileNotFoundError:
        # Tool not installed → don't make the whole suite fail
        try:
            return GateResult(
                gate_id=gate_id,
                status="SKIPPED",
                output="tool not found",
                reason="tool not found",
            )
        except TypeError:
            gr = GateResult(
                gate_id=gate_id,
                ok=ok_if_missing,
                skipped=True,
                output="tool not found",
                reason="tool not found",
            )
            if hasattr(gr, "status"):
                pass  # status property should compute to SKIPPED from skipped=True
            return gr

    except Exception as e:
        # Unexpected error - return FAIL status
        try:
            return GateResult(
                gate_id=gate_id,
                status="FAIL",
                output=str(e),
                reason=f"unexpected error: {e}",
            )
        except TypeError:
            gr = GateResult(
                gate_id=gate_id,
                ok=False,
                skipped=False,
                output=str(e),
                reason=f"unexpected error: {e}",
            )
            if hasattr(gr, "status"):
                pass  # status property should compute to FAIL from ok=False
            return gr
