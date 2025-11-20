"""Executor package for FirstTry DAG execution."""

from typing import TYPE_CHECKING

__all__ = ["dag", "execute_plan", "run_command"]

if TYPE_CHECKING:
    from typing import Any

    def run_command(cmd: str, cwd: str) -> dict: ...

    def execute_plan(
        plan: dict,
        autofix: bool = False,
        interactive_autofix: bool = True,
        max_tier: Any | None = None,
    ) -> dict: ...

# Re-export the legacy top-level `executor.py` helpers (if present) so
# callers that import `firsttry.executor.execute_plan` continue to work
# even though there's also an `executor/` package.
try:
    from .. import executor as _legacy_executor

    execute_plan = _legacy_executor.execute_plan
    run_command = _legacy_executor.run_command
except Exception:
    # Best-effort: don't raise at import time if the legacy module is missing
    pass
