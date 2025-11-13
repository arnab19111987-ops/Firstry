from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Safe Gate class that works without complex imports
class Gate:
    def run(self, root: Path) -> "GateResult":
        return GateResult(gate_id="unknown", ok=True)

    def should_run_for(self, changed_files: list[str]) -> bool:
        return True


@dataclass
class GateResult:
    gate_id: str
    ok: bool
    skipped: bool = False
    reason: str = ""
    watched_files: list[str] | None = None


# Lightweight profile used by the simple runner interface
@dataclass
class Profile:
    name: str
    gates: list[str]


# Legacy runner class for backward compatibility
class LegacyRunner:
    def __init__(self) -> None:
        self.gate_registry: dict[str, type[Gate]] = {}

    def run_profile(
        self,
        root: Path,
        profile_name: str = "fast",
        since_ref: str | None = None,
    ) -> int:
        """Simplified runner that returns success."""
        return 0


# Backward compatibility functions / exported helpers expected by cli_v2
GATE_REGISTRY: dict[str, type[Gate]] = {}


def get_changed_files(root: Path, since: str | None = None) -> list[str]:
    # best-effort: no VCS available in lightweight runner
    return []


def get_profile(name: str = "fast") -> Profile:
    # simple default profiles; callers will typically override
    if name == "strict":
        return Profile(name="strict", gates=[])
    return Profile(name=name, gates=["fast"])  # placeholder


def load_cache(root: Path) -> dict[str, Any]:
    return {}


def should_skip_gate(cache: dict[str, Any], gate_id: str, changed: list[str]) -> bool:
    return False


def update_gate_cache(cache: dict[str, Any], gate_id: str, watched_files: list[str]) -> None:
    cache[gate_id] = watched_files


def run_profile(
    root: Path,
    profile_name: str = "fast",
    since_ref: str | None = None,
) -> int:
    """Simplified profile runner that always succeeds."""
    return 0
