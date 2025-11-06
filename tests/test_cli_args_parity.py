"""
Regression tests to prevent CLI argument regressions (like --report ambiguity).
Tests that critical flags work and match CI-Green Guarantee surface.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "args",
    [
        ["--tier", "lite", "--report-json", os.devnull, "--report-schema", "2", "--dry-run"],
        ["--tier", "lite"],  # common fast path
        ["--tier", "pro"],
        ["--profile", "fast"],
        ["--profile", "strict"],
    ],
)
def test_cli_accepts_critical_args(args):
    """
    Ensure critical CLI args are not regressed.
    This would catch regressions like the --report ambiguity that broke CI.
    """
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    cmd = [sys.executable, "-m", "firsttry.cli", "run"] + args
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
    
    # Check for argparse errors (like "ambiguous option" or "unrecognized arguments")
    if "ambiguous option" in result.stderr or "unrecognized arguments" in result.stderr:
        pytest.fail(f"CLI flag regression detected:\nCmd: {' '.join(cmd)}\nError: {result.stderr}")
    
    # For dry-run, returncode 0 is expected
    # For others, we just want to ensure no parser errors
    assert result.returncode in (0, 1, 2), (
        f"Unexpected return code: {result.returncode}\n"
        f"Cmd: {' '.join(cmd)}\n"
        f"Stderr: {result.stderr}\n"
        f"Stdout: {result.stdout}"
    )


def test_cli_no_ambiguous_flags():
    """
    Ensure no ambiguous flags in parser (regression: --report was ambiguous).
    """
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    
    # Request help to parse parser structure
    cmd = [sys.executable, "-m", "firsttry.cli", "run", "--help"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=5)
    
    # Check for any mention of "ambiguous" in help or error
    assert "ambiguous" not in result.stderr.lower(), (
        f"Ambiguous options found in CLI parser:\n{result.stderr}"
    )
    
    # Ensure common flags are documented
    assert "--tier" in result.stdout, "Missing --tier flag in CLI"
    assert "--dry-run" in result.stdout, "Missing --dry-run flag in CLI"
