"""Planner package for FirstTry."""

from typing import TYPE_CHECKING

__all__ = ["dag", "build_plan"]

# Re-export the legacy top-level `planner.py` helper so callers can import
# `firsttry.planner.build_plan` even though a `planner/` package exists.
try:
    from .. import planner as _legacy_planner

    build_plan = _legacy_planner.build_plan
except Exception:
    pass


if TYPE_CHECKING:
    def build_plan(root: str = ".") -> dict: ...
