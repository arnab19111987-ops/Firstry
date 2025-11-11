"""CI files changed gate implementation."""

from typing import Any

from .base import Gate, GateResult


class CiFilesChangedGate(Gate):
    """Gate that checks if CI files have changed."""

    gate_id = "ci_files_changed"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Check if CI files have changed."""
        # This is a placeholder implementation
        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            skipped=True,
            reason="CI files changed check not implemented, skipping",
        )
