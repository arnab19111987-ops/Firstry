import asyncio
import asyncio

from firsttry.checks_orchestrator import _run_bucket_with_timeout


def test_cmd_item_without_custom_runner_fails_gracefully():
    async def _go():
        item = {"tool": "nonexistent_tool", "cmd": "echo hello"}
        result = await _run_bucket_with_timeout(
            [item], allocation={}, ctx={}, tier=None, config=None, timeout_seconds=5.0
        )

        out = result[0] if isinstance(result, list) and result else result

        assert isinstance(out, dict)
        assert out.get("status") == "error" or out.get("ok") is False or "error" in out
        return out

    result = asyncio.run(_go())
    # Assert the command string is surfaced to aid debugging
    assert "echo hello" in (result.get("message") or "")
