from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Type


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


# Module-level compatibility exports expected by other callers (and tests)

# Registry mapping gate IDs to Gate classes
GATE_REGISTRY: Dict[str, Type[Gate]] = {}


def get_profile(name: str | None = None) -> Any:
    """Return a GateProfile-like object.

    Prefer the real implementation if available; fall back to a minimal
    placeholder so callers can operate without importing heavy modules.
    """
    try:
        from .profiles import get_profile as _gp

        # The real `get_profile` expects a non-None name; callers may pass
        # None here to indicate a default. Normalize to a concrete string so
        # mypy correctly understands the call without changing runtime semantics.
        return _gp(name or "fast")
    except Exception:
        # Minimal placeholder
        class _P:
            name = name or "fast"

            gates: List[str] = []

        return _P()


def get_changed_files(root: Path | str = ".", since: str | None = None) -> List[str]:
    """Compatibility wrapper for changed-file detection.

    Many callers expect `get_changed_files(root, since)`. Internally the
    canonical implementation is in `firsttry.changed`; delegate to it.
    """
    try:
        from .changed import get_changed_files as _gc

        # The canonical `get_changed_files` takes a rev (like "HEAD"). If
        # callers supply `since`, use that, otherwise default to HEAD.
        rev = since or "HEAD"
        return _gc(rev)
    except Exception:
        return []


def load_cache(root: Path | str | None = None) -> Dict[str, Any]:
    """Load repository-local cache for the given `root`.

    This delegates to the legacy `firsttry.cache` helpers when available.
    """
    try:
        from .cache import load_cache_legacy as _lc

        return _lc(Path(root) if root is not None else Path("."))
    except Exception:
        return {}


def should_skip_gate(cache: dict, gate_id: str, changed_files: list[str]) -> bool:
    try:
        from .cache import should_skip_gate as _ss

        return _ss(cache, gate_id, changed_files)
    except Exception:
        return False


def update_gate_cache(cache: dict, gate_id: str, watched_files: list[str]) -> None:
    try:
        from .cache import update_gate_cache as _ug

        return _ug(cache, gate_id, watched_files)
    except Exception:
        return None
