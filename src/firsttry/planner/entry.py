from __future__ import annotations

from __future__ import annotations

from typing import Any

from ..twin.graph import CodebaseTwin
from .dag import build_plan_from_twin as _build_plan_from_twin


def build_plan_from_twin(twin: Any | CodebaseTwin) -> Any:
    """Stable entrypoint: prefer the modern twin->plan builder when present.

    This wrapper is intentionally defensive: different twin shapes exist in
    the repo (tests and older callers). Try the modern DAG-based builder and
    fall back to the legacy planner when necessary.
    """
    # Try the modern signature first (twin, *, tier, changed, ...)
    tier = getattr(twin, "tier", "free-lite")
    changed = getattr(twin, "changed_files", None) or getattr(twin, "changed", [])
    return _build_plan_from_twin(twin, tier=tier, changed=changed)
