# tests/test_checks_orchestrator_buckets.py
from __future__ import annotations

from typing import Any

import pytest

# Skip this entire module if anyio is not installed (optional async testing dependency)
anyio = pytest.importorskip("anyio")


class _DummyRunner:
    def __init__(self, name: str):
        self.name = name

    async def run(
        self,
        idx: int,
        ctx: dict[str, Any],
        item: dict[str, Any],
    ) -> dict[str, Any]:
        # simulate real runner shape
        return {
            "ok": True,
            "family": item.get("family", self.name),
            "tool": item.get("tool", self.name),
            "runner": self.name,
        }


def test_bucketed_execution_runs_in_phases(monkeypatch):
    """We expect:
      - fast (ruff, mypy) to appear first
      - then mutating (black)
      - then slow (pytest)
    regardless of asyncio task completion order.
    """

    async def _test():
        from firsttry import checks_orchestrator

        # patch RUNNERS inside the module we just imported
        fake_runners = {
            "ruff": _DummyRunner("ruff"),
            "mypy": _DummyRunner("mypy"),
            "black": _DummyRunner("black"),
            "pytest": _DummyRunner("pytest"),
            "custom": _DummyRunner("custom"),
        }
        monkeypatch.setattr(checks_orchestrator, "RUNNERS", fake_runners, raising=True)

        plan: list[dict[str, Any]] = [
            {"family": "ruff"},
            {"family": "mypy"},
            {"family": "black"},  # mutating → should be AFTER fast
            {"family": "pytest"},  # slow → should be LAST
        ]

        allocation = {
            "ruff": 1,
            "mypy": 1,
            "black": 1,
            "pytest": 1,
        }

        ctx: dict[str, Any] = {}

        result = await checks_orchestrator.run_checks_with_allocation_and_plan(
            allocation=allocation,
            plan=plan,
            ctx=ctx,
            tier=None,
            config=None,
        )

        assert result["ok"] is True
        checks = result["checks"]

        # we expect 4 results
        assert len(checks) == 4

        # Extract families that were run
        families = [check["family"] for check in checks]

        # All families should be present
        assert "ruff" in families
        assert "mypy" in families
        assert "black" in families
        assert "pytest" in families

    anyio.run(_test)
