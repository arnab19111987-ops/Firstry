import asyncio
import os
from pathlib import Path

from firsttry.checks_orchestrator import run_orchestrator


def test_concurrency_cap_applies():
    # Enable debug telemetry inside run_cmd
    os.environ["FT_DEBUG_CONCURRENCY"] = "1"

    # Build a plan with several custom commands that sleep briefly
    plan = [
        {"id": f"sleep-{i}", "family": "custom", "tool": "custom", "cmd": "/bin/sleep 0.25"}
        for i in range(6)
    ]

    # Request many workers for the custom family; the orchestrator should clamp
    allocation = {"custom": 6}

    ctx = {"repo_root": str(Path('.').resolve())}

    # Ask orchestrator to limit to 2 workers via config
    config = {"runner": {"max_workers": 2}}

    res = asyncio.run(run_orchestrator(allocation, plan, ctx, config=config))

    # Telemetry should have been populated by run_cmd (guarded by FT_DEBUG_CONCURRENCY)
    max_seen = ctx.get("_max_concurrency_seen", 0)
    assert max_seen <= 2, f"Expected max concurrency <= 2, got {max_seen}"
    assert res.get("ok", False) is True
