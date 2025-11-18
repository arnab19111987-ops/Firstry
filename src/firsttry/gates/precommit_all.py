"""Pre-commit all gate implementation."""

from typing import Any

from .base import Gate, GateResult


class PreCommitAllGate(Gate):
    """Gate that runs all pre-commit checks."""

    gate_id = "precommit_all"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Run all pre-commit checks."""
        # This is a placeholder implementation
        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            skipped=True,
            reason="pre-commit all check not implemented, skipping",
        )
