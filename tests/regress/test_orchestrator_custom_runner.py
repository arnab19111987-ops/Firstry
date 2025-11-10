import asyncio
import pytest

# The module name may be firsttry.checks_orchestrator in your tree.
from firsttry.checks_orchestrator import _run_bucket_with_timeout

@pytest.mark.asyncio
async def test_cmd_item_without_custom_runner_fails_gracefully():
    # Force a 'cmd' plan item so the orchestrator looks for a 'custom' runner.
    item = {"tool": "nonexistent_tool", "cmd": "echo hello"}
    out = await _run_bucket_with_timeout(item, ctx={}, timeout_seconds=5)

    # PRE-FIX this may crash; POST-FIX expect a structured error dict.
    assert isinstance(out, dict)
    # Accept a few possible keys that indicate an error result
    assert any(k in out for k in ("status", "ok", "error"))
    # message should mention missing custom runner
    msg = (out.get("message") or out.get("error") or "").lower()
    assert "custom" in msg or "runner" in msg or not out.get("ok", True)
