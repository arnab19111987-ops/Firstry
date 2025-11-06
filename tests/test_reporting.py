"""
Regression tests for reporting functionality to ensure schema stability.
These tests are robust to optional CLI flags and import differences between builds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from firsttry.reporting import print_summary
from firsttry.gates.base import GateResult


def _run(cmd: List[str], *, cwd: Path | None = None, env: dict | None = None, timeout: int = 90) -> subprocess.CompletedProcess:
    """Run a subprocess with sane defaults and captured output."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _cli_has_flag(module: str, subcmd: List[str], flag: str) -> bool:
    """
    Return True if `python -m module <subcmd> --help` mentions `flag`.
    We avoid importing the CLI in-process to sidestep side effects.
    """
    help_proc = _run([sys.executable, "-m", module, *subcmd, "--help"])
    return help_proc.returncode == 0 and flag in help_proc.stdout


@pytest.mark.integration
def test_cli_run_writes_report_when_supported(tmp_path: Path, monkeypatch):
    """
    If the CLI supports a debug/report flag, ensure it writes a valid JSON report
    with locked schema (non-empty, schema_version present, core keys present).
    If the flag isn't supported in this build, we skip instead of failing.
    """
    monkeypatch.chdir(tmp_path)

    # Minimal repo marker so language detection doesn't no-op
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n")

    # Prepare environment to ensure local import of `src/`
    env = os.environ.copy()
    # Prefer repo-local src when the tests run from the project root
    # (adjust path if test file lives under tests/)
    repo_src = Path(__file__).resolve().parent.parent / "src"
    env["PYTHONPATH"] = f"{repo_src}:{env.get('PYTHONPATH','')}"

    # Feature-detect flags
    supports_debug_report = _cli_has_flag("firsttry.cli", ["run"], "--debug-report") or _cli_has_flag(
        "firsttry.cli_run_profile", [], "--debug-report"
    )

    if not supports_debug_report:
        pytest.skip("CLI does not expose --debug-report in this build")

    # Prefer the modern entrypoint if present; otherwise fall back
    # to the legacy cli_run_profile module.
    use_mod = "firsttry.cli" if _cli_has_flag("firsttry.cli", ["run"], "--debug-report") else "firsttry.cli_run_profile"

    # Some builds accept --repo, some infer CWD; we set CWD and pass --repo if supported
    supports_repo_flag = _cli_has_flag(use_mod, ["run"] if use_mod.endswith(".cli") else [], "--repo")

    cmd = [sys.executable, "-m", use_mod]
    if use_mod.endswith(".cli"):
        cmd += ["run", "--tier", "free-lite", "--debug-report"]
        if supports_repo_flag:
            cmd += ["--repo", "."]
    else:
        # legacy runner
        cmd += ["--debug-report"]
        if supports_repo_flag:
            cmd += ["--repo", "."]

    proc = _run(cmd, cwd=tmp_path, env=env, timeout=90)
    assert proc.returncode == 0, f"CLI failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    report_path = tmp_path / ".firsttry" / "last_run.json"
    assert report_path.exists(), "Report file was not written"

    report_text = report_path.read_text(encoding="utf-8")
    assert report_text.strip(), "Report file is empty"

    data = json.loads(report_text)

    # Schema lock (update expected value if your schema_version bumps)
    assert "schema_version" in data, "schema_version missing"
    assert data["schema_version"] == 1, f"unexpected schema version: {data['schema_version']}"

    # Required top-level
    for key in ("repo", "run_at", "timing", "checks"):
        assert key in data, f"{key} missing"

    # Timing fields present and numeric
    timing = data["timing"]
    for key in ("detect_ms", "fast_ms", "mutating_ms", "slow_ms", "total_ms"):
        assert key in timing, f"{key} missing from timing"
        assert isinstance(timing[key], (int, float)), f"{key} should be numeric"

    # Checks array sanity
    checks = data["checks"]
    assert isinstance(checks, list), "checks should be an array"
    for check in checks:
        assert "name" in check, "check missing name"
        assert "status" in check, "check missing status"
        assert "duration_s" in check, "check missing duration_s"
        if "last_duration_s" in check:
            assert isinstance(check["last_duration_s"], (int, float)), "last_duration_s should be numeric"


@pytest.mark.integration
def test_cli_shows_timing_when_write_fails(tmp_path: Path, monkeypatch):
    """
    If the report target is unwritable and the CLI supports a --report flag,
    the process should still succeed and include timing in stdout (graceful degradation).
    If the flag isn't supported in this build, we skip instead of failing.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n")

    env = os.environ.copy()
    repo_src = Path(__file__).resolve().parent.parent / "src"
    env["PYTHONPATH"] = f"{repo_src}:{env.get('PYTHONPATH','')}"

    # Detect support
    candidates = [("firsttry.cli", ["run"]), ("firsttry.cli_run_profile", [])]
    use_mod, subcmd = None, None
    for mod, sc in candidates:
        if _cli_has_flag(mod, sc, "--report"):
            use_mod, subcmd = mod, sc
            break
    if use_mod is None:
        pytest.skip("CLI does not expose --report in this build")

    cmd = [sys.executable, "-m", use_mod, *subcmd]
    if subcmd == ["run"]:
        cmd += ["--tier", "free-lite"]
    # Attempt to write to a typically read-only file to force a write failure
    cmd += ["--report", "/proc/version"]

    proc = _run(cmd, cwd=tmp_path, env=env, timeout=90)
    # We expect graceful success (return code 0) despite failed write
    assert proc.returncode == 0, f"CLI should succeed even if report write fails:\n{proc.stderr}"

    stdout = proc.stdout or ""
    # Either an explicit warning or visible timing fields in stdout
    has_warning = "failed to write timing report" in stdout.lower() or "warning: failed to write" in stdout.lower()
    has_timing = any(k in stdout for k in ("total_ms", "fast_ms", "slow_ms", "detect_ms"))
    assert has_warning or has_timing, f"Expected timing fallback or warning in stdout.\nOutput:\n{stdout}"


def test_print_summary_formats_output(capsys):
    results = [
        GateResult(gate_id="python:ruff", ok=True),
        GateResult(gate_id="python:mypy", ok=False, output="error"),
        GateResult(gate_id="security:bandit", ok=True, skipped=True, reason="not installed"),
    ]
    print_summary(results)
    out = capsys.readouterr().out
    assert "FirstTry Summary" in out
    assert "python:ruff" in out
    assert "python:mypy" in out
    assert "Failed: 1" in out
