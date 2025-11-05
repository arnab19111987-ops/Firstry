"""
Regression tests for reporting functionality to ensure schema stability.
"""
from pathlib import Path
import json
import subprocess
import sys

from firsttry.reporting import print_summary
from firsttry.gates.base import GateResult


def test_cli_run_profile_writes_report(tmp_path: Path, monkeypatch):
    """
    Test that cli_run_profile writes a valid report with locked schema.
    This is a regression test to ensure the exact bug we fixed doesn't happen again:
    "CLI succeeds but file is empty."
    """
    # run inside temp dir to avoid polluting real .firsttry
    monkeypatch.chdir(tmp_path)

    # create fake repo with Python markers so detection works
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n")

    # run the CLI (using the test module directly)
    cmd = [
        sys.executable,
        "-m",
        "firsttry.cli_run_profile",
        "--repo",
        ".",
        "--debug-report",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    # Should succeed
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}"

    # Report file should exist
    report_path = tmp_path / ".firsttry" / "last_run.json"
    assert report_path.exists(), "report file not written"

    # Should be valid JSON
    report_text = report_path.read_text()
    assert report_text.strip(), "report file is empty"

    data = json.loads(report_text)

    # Schema version lock - this is the main regression protection
    assert "schema_version" in data, "schema_version missing"
    assert (
        data["schema_version"] == 1
    ), f"unexpected schema version: {data['schema_version']}"

    # Required top-level fields
    assert "repo" in data, "repo missing"
    assert "run_at" in data, "run_at timestamp missing"
    assert "timing" in data, "timing missing"
    assert "checks" in data, "checks array missing"

    # Timing must have all 5 fields
    timing = data["timing"]
    required_timing_fields = [
        "detect_ms",
        "fast_ms",
        "mutating_ms",
        "slow_ms",
        "total_ms",
    ]
    for key in required_timing_fields:
        assert key in timing, f"{key} missing from timing"
        assert isinstance(timing[key], (int, float)), f"{key} should be numeric"

    # Checks should be an array
    checks = data["checks"]
    assert isinstance(checks, list), "checks should be array"

    # Each check should have required fields
    for check in checks:
        assert "name" in check, "check missing name"
        assert "status" in check, "check missing status"
        assert "duration_s" in check, "check missing duration_s"
        # last_duration_s is optional but if present should be numeric
        if "last_duration_s" in check:
            assert isinstance(
                check["last_duration_s"], (int, float)
            ), "last_duration_s should be numeric"


def test_cli_error_handling_shows_timing(tmp_path: Path, monkeypatch):
    """
    Test that when report writing fails, timing is still shown to stdout.
    This ensures CI/CD and humans can scrape the timing even if filesystem issues occur.
    """
    # run inside temp dir
    monkeypatch.chdir(tmp_path)

    # create fake repo
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n")

    # Try to write to an invalid location (like /proc/version which is read-only)
    cmd = [
        sys.executable,
        "-m",
        "firsttry.cli_run_profile",
        "--repo",
        ".",
        "--report",
        "/proc/version",  # This should fail to write
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    # Should still succeed (graceful failure)
    assert (
        proc.returncode == 0
    ), f"CLI should succeed even if report write fails: {proc.stderr}"

    # Should show warning about failed write
    assert (
        "warning: failed to write timing report" in proc.stdout
    ), "Should show write failure warning"

    # Should show timing data in stdout as fallback
    output_lines = proc.stdout.split("\n")
    timing_shown = False
    for line in output_lines:
        if "total_ms" in line or "fast_ms" in line:
            timing_shown = True
            break

    assert (
        timing_shown
    ), f"Timing should be shown in stdout when write fails. Output: {proc.stdout}"


def test_print_summary(capsys):
    results = [
        GateResult(gate_id="python:ruff", ok=True),
        GateResult(gate_id="python:mypy", ok=False, output="error"),
        GateResult(
            gate_id="security:bandit", ok=True, skipped=True, reason="not installed"
        ),
    ]
    print_summary(results)
    out = capsys.readouterr().out
    assert "FirstTry Summary" in out
    assert "python:ruff" in out
    assert "python:mypy" in out
    assert "Failed: 1" in out
