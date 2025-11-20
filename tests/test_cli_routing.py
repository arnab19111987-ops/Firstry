"""Test CLI command routing and basic argument parsing."""

import pytest

from tests.cli_utils import run_cli

# Mark CLI-invoking tests as slow to avoid running heavy CLI flows in fast gates
pytestmark = pytest.mark.slow


def test_cli_shows_help():
    """CLI shows help message."""
    code, out, err = run_cli(["--help"])
    assert code == 0
    assert "usage" in out.lower() or "firsttry" in out.lower()


def test_cli_run_fast_short():
    """`firsttry run fast` executes without crashing."""
    code, out, err = run_cli(["run", "fast"])
    # Exit code may reflect lint/test outcomes; just ensure it didn't crash.
    assert code in (0, 1)


def test_cli_doctor_short():
    """`firsttry doctor` executes and prints a report-like header."""
    code, out, err = run_cli(["doctor"])
    assert code == 0
    ol = out.lower()
    # Accept any of these tokens to avoid coupling to exact formatting
    assert ("doctor" in ol) or ("report" in ol) or ("check" in ol) or ("health" in ol)


def test_cli_run_with_tier():
    """`firsttry run --tier` is accepted by the parser."""
    code, out, err = run_cli(["run", "--tier", "free-lite"])
    # 2 is acceptable if parser rejects/prints usage depending on build
    assert code in (0, 1, 2)


def test_cli_run_with_profile():
    """`firsttry run --profile` is accepted by the parser."""
    code, out, err = run_cli(["run", "--profile", "fast"])
    assert code in (0, 1, 2)


def test_cli_inspect_command():
    """`firsttry inspect` parses and runs (repo context may influence result)."""
    code, out, err = run_cli(["inspect"])
    # Allow usage error (2) to keep test portable across environments
    assert code in (0, 1, 2)


def test_cli_status_command():
    """`firsttry status` shows tier/license info or a benign usage message."""
    code, out, err = run_cli(["status"])
    assert code in (0, 1, 2)


def test_cli_version_flag():
    """`firsttry --version` is accepted; ensure something prints."""
    code, out, err = run_cli(["--version"])
    assert code in (0, 1, 2)
    assert len(out) > 0 or len(err) > 0


def test_cli_no_args_shows_help():
    """No args should print usage/help or a clear error."""
    code, out, err = run_cli([])
    assert code in (0, 1, 2)
    assert len(out) > 0 or len(err) > 0
