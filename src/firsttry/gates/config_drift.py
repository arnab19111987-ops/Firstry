"""Config drift gate implementation."""

from typing import Any

from .base import Gate, GateResult


class ConfigDriftGate(Gate):
    """Gate that checks for configuration drift."""

    gate_id = "config_drift"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Check for configuration drift."""
        # This is a placeholder implementation
        # In a real scenario, this would check for configuration drift
        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            skipped=True,
            reason="config drift check not implemented, skipping",
        )
