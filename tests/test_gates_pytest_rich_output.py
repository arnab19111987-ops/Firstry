"""Regression test: check_tests() must return rich output, not just ok/fail.

This prevents accidentally simplifying check_tests() to use _safe_gate()
which would lose the pytest output parsing that extracts test counts.
"""

from __future__ import annotations

import subprocess

import pytest

import firsttry.gates as gates_mod
from firsttry.gates import check_tests


@pytest.mark.timeout(120)  # This test runs pytest recursively, needs more time
def test_check_tests_has_rich_info(monkeypatch):
    """check_tests() must return structured info about pytest results.

    If pytest is not installed, it should return a skipped result with
    a clear reason. If pytest runs, it should parse the output and
    include test information in the result.
    """
    # Patch the gate's subprocess.run so we don't spawn a real pytest child process.
    fake_stdout = "1 passed in 0.01s\nsome rich info\n"

    def fake_run(
        cmd, capture_output=True, text=True, check=False, env=None, timeout=None, **kwargs
    ):
        # Mirror subprocess.CompletedProcess enough for the gate logic.
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=fake_stdout, stderr="")

    monkeypatch.setattr(gates_mod.subprocess, "run", fake_run)

    res = check_tests()

    # Must have a GateResult-like structure
    assert hasattr(res, "ok")
    assert hasattr(res, "skipped")

    if res.skipped:
        # If pytest not installed, must have clear skip reason
        reason = res.reason or ""
        assert "not found" in reason or "skip" in reason.lower(), (
            f"Skipped gate should have clear reason, got: {reason}"
        )
    else:
        # When pytest runs, must provide rich info
        # Check that we have meaningful output or reason
        output = getattr(res, "output", "") or ""
        reason = getattr(res, "reason", "") or ""
        details = getattr(res, "details", "") or ""

        combined_text = (output + reason + details).lower()

        # Should mention "test" somewhere (e.g., "23 tests", "pytest tests")
        assert "test" in combined_text, (
            f"Gate should include test info. Got output={output!r}, reason={reason!r}, details={details!r}"
        )


def test_check_tests_info_contains_count_when_successful(monkeypatch):
    """When pytest succeeds, check_tests() should parse output and include
    test count in the info/reason field (e.g., "23 tests").
    """
    import subprocess

    def fake_run(cmd, capture_output=None, text=None, check=False, env=None, **kwargs):
        """Simulate successful pytest run."""
        return type(
            "FakeResult",
            (),
            {"returncode": 0, "stdout": "23 passed in 1.5s\n", "stderr": ""},
        )()

    monkeypatch.setattr(subprocess, "run", fake_run)

    res = check_tests()

    assert res.ok is True
    assert res.skipped is False

    # The critical assertion: must have parsed the count
    info = getattr(res, "info", None) or getattr(res, "reason", None) or ""
    assert "23 tests" in info, f"Expected '23 tests' in info/reason, got: {info!r}"
