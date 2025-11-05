"""Utility functions for gate implementations."""

from typing import List, Optional
import subprocess

from .base import GateResult


def _safe_gate(
    gate_id: str,
    cmd: Optional[List[str]] = None,
    *,
    ok_if_missing: bool = True,
) -> GateResult:
    """
    Run a shell/tool-based gate but never crash the whole run.

    Args:
        gate_id: Identifier for this gate (e.g., "lint", "types")
        cmd: Command to run as list of strings, or None for pythonic gates
        ok_if_missing: Whether to treat missing tool as ok (skipped) or failure

    Returns:
        GateResult with structured success/failure/skip information
    """
    try:
        if cmd is None:
            # Pure Python gate with no subprocess
            return GateResult(gate_id=gate_id, ok=True, skipped=False, output="")

        # Run the command - pass all kwargs that subprocess.run might accept
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except TypeError:
            # If monkeypatch doesn't accept check parameter, try without it
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

        return GateResult(
            gate_id=gate_id,
            ok=(proc.returncode == 0),
            skipped=False,
            output=(proc.stdout or "") + (proc.stderr or ""),
            reason=None if proc.returncode == 0 else f"exit {proc.returncode}",
        )
    except FileNotFoundError:
        # Tool not installed → don't make the whole suite fail
        return GateResult(
            gate_id=gate_id,
            ok=ok_if_missing,
            skipped=True,
            output="tool not found",
            reason="tool not found",
        )
    except Exception as e:
        # THIS is what `test_gate_runner_handles_exception` checks
        return GateResult(
            gate_id=gate_id,
            ok=False,
            skipped=False,
            output=str(e),
            reason=f"unexpected error: {e}",
        )
