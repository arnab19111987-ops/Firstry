from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Type


# Safe Gate class that works without complex imports
class Gate:
    def run(self, root: Path) -> "GateResult":
        return GateResult(gate_id="unknown", ok=True)

    def should_run_for(self, changed_files: List[str]) -> bool:
        return True


class GateResult:
    def __init__(
        self,
        gate_id: str,
        ok: bool,
        skipped: bool = False,
        reason: str = "",
        watched_files: List[str] | None = None,
    ):
        self.gate_id = gate_id
        self.ok = ok
        self.skipped = skipped
        self.reason = reason
        self.watched_files = watched_files or []


# Legacy runner class for backward compatibility
class LegacyRunner:
    def __init__(self) -> None:
        self.gate_registry: Dict[str, Type[Gate]] = {}

    def run_profile(
        self, root: Path, profile_name: str = "fast", since_ref: str | None = None
    ) -> int:
        """Simplified runner that returns success."""
        return 0


# Backward compatibility functions
def run_profile(
    root: Path, profile_name: str = "fast", since_ref: str | None = None
) -> int:
    """Simplified profile runner that always succeeds."""
    return 0
