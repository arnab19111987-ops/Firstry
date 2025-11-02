# tests/test_checks_orchestrator_buckets.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest
import anyio


class _DummyRunner:
    def __init__(self, name: str):
        self.name = name

    async def run(self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        # simulate real runner shape
        return {
            "ok": True,
            "family": item.get("family", self.name),
            "tool": item.get("tool", self.name),
            "runner": self.name,
        }


def test_bucketed_execution_runs_in_phases(monkeypatch):
    """
    We expect:
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

        plan: List[Dict[str, Any]] = [
            {"family": "ruff"},
            {"family": "mypy"},
            {"family": "black"},   # mutating → should be AFTER fast
            {"family": "pytest"},  # slow → should be LAST
        ]

        allocation = {
            "ruff": 1,
            "mypy": 1,
            "black": 1,
            "pytest": 1,
        }

        ctx: Dict[str, Any] = {}

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

        # order must be: ruff, mypy, black, pytest
        assert checks[0]["family"] == "ruff"
        assert checks[1]["family"] == "mypy"
        assert checks[2]["family"] == "black"
        assert checks[3]["family"] == "pytest"

    anyio.run(_test)