"""
Runners registry and lightweight defaults.

This module exposes a `RUNNERS` mapping used by the orchestrator. By default
we populate `RUNNERS` from `registry.default_registry()` and ensure a
`"custom"` runner is always present. An environment flag
`FIRSTTRY_USE_REAL_RUNNERS` can still opt-in to real implementations.
"""

import os
from typing import Any, Dict

from .registry import default_registry
from .custom import CustomRunner

__all__ = [
    "RUNNERS",
]


# Start from the default registry (provides ruff/mypy/pytest runner instances)
try:
    RUNNERS: Dict[str, Any] = default_registry()
except Exception:
    # Fallback to an empty dict if registry import fails for some reason
    RUNNERS = {}

# Ensure a 'custom' runner is always available (used when an item has a `cmd`)
try:
    if "custom" not in RUNNERS:
        RUNNERS["custom"] = CustomRunner()
except Exception:
    # If constructing CustomRunner fails for any reason, ensure key exists
    RUNNERS.setdefault("custom", None)

# Optional: if real runners are requested, attempt to import and update registry
if os.getenv("FIRSTTRY_USE_REAL_RUNNERS") in ("1", "true", "True"):
    try:
        from . import real as _real  # type: ignore

        # If the real module exposes a mapping, merge it
        real_map = getattr(_real, "REAL_RUNNERS", None)
        if isinstance(real_map, dict):
            RUNNERS.update(real_map)
    except Exception:
        # keep the default registry if real runners fail to load
        pass
