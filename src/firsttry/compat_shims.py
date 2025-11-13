from __future__ import annotations

# Lightweight shim so older import paths continue to work:
#   from firsttry.compat_shims import build_plan
# We delegate to the modern planner API when available.
try:
    from .planner.dag import build_plan_from_twin as build_plan  # type: ignore
except Exception:  # pragma: no cover
    # Fallback: provide a no-op stub to avoid import-time crashes
    def build_plan(*_args, **_kwargs):  # type: ignore
        return None

# Also provide a no-op execute_plan for legacy import sites that expect it.
def execute_plan(*_args, **_kwargs):  # type: ignore
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
