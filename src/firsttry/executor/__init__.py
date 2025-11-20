"""Executor package for FirstTry DAG execution."""
__all__ = ["dag", "execute_plan", "run_command"]

# Re-export the legacy top-level `executor.py` helpers (if present) so
# callers that import `firsttry.executor.execute_plan` continue to work
# even though there's also an `executor/` package.
try:
	from .. import executor as _legacy_executor

	execute_plan = _legacy_executor.execute_plan  # type: ignore[attr-defined]
	run_command = _legacy_executor.run_command  # type: ignore[attr-defined]
except Exception:
	# Best-effort: don't raise at import time if the legacy module is missing
	pass
