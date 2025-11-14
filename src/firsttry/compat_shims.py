# Lightweight shim so older import paths continue to work:
#   from firsttry.compat_shims import build_plan
# We delegate to the modern planner API when available.
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import Mapping

# Lightweight shim so older import paths continue to work:
try:
    from .planner.dag import build_plan_from_twin as build_plan
except Exception:  # pragma: no cover
    # Fallback: provide a typed stub matching the planner signature to satisfy
    # static checkers. We import types only for annotations to avoid runtime
    # cyclic imports.
    if TYPE_CHECKING:
        from .planner.dag import CodebaseTwin
        from .planner.dag import Plan

    def build_plan(
        twin: "CodebaseTwin",
        *,
        tier: str,
        changed: list[str],
        workflow_requires: Mapping[str, Iterable[str]] | None = None,
        pytest_shards: int = 1,
    ) -> "Plan":
        raise NotImplementedError


# Also provide a no-op execute_plan for legacy import sites that expect it.
def execute_plan(*_args, **_kwargs):
    return None


# Reporting helpers expected by some legacy imports/tests. Keep them tiny and
# async-compatible so callers can await write_report_async when present.
def print_report(report: object) -> None:  # pragma: no cover - shim
    try:
        import json

        print(json.dumps(report, indent=2))
    except Exception:
        print(str(report))


async def write_report_async(path, payload):  # pragma: no cover - shim
    # Minimal async writer used by tests; keeps signature compatible.
    try:
        from pathlib import Path

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(__import__("json").dumps(payload, indent=2))
    except Exception:
        return None


__all__ = ["build_plan", "execute_plan", "print_report", "write_report_async"]
