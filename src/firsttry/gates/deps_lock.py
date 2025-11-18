"""Dependencies lock gate implementation."""

from typing import Any

from .base import Gate, GateResult


class DepsLockGate(Gate):
    """Gate that checks for dependency lock files."""

    gate_id = "deps_lock"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Check for dependency lock files."""
        # This is a placeholder implementation. In a real scenario this would
        # check for lock files like poetry.lock or package-lock.json, etc.
        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            skipped=True,
            reason="dependency lock check not implemented, skipping",
        )
