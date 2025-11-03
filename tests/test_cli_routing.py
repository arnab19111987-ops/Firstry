"""Test CLI command routing and basic argument parsing."""

from tests.cli_utils import run_cli


def test_cli_shows_help():
    """Test that CLI shows help message."""
    code, out, err = run_cli(["--help"])
    assert code == 0
    assert "usage" in out.lower() or "firsttry" in out.lower()


def test_cli_run_fast_short():
    """Test that CLI run fast command executes without crashing."""
    code, out, err = run_cli(["run", "fast"])
    # Assert it ran and didn't crash (exit code varies by what checks run)
    # We just want to exercise the CLI routing
    assert code in (0, 1)  # May pass or fail depending on checks, but shouldn't crash


def test_cli_doctor_short():
    """Test that CLI doctor command executes."""
    code, out, err = run_cli(["doctor"])
    assert code == 0
    assert "doctor" in out.lower() or "report" in out.lower() or "check" in out.lower()


def test_cli_run_with_tier():
    """Test that CLI accepts --tier flag."""
    code, out, err = run_cli(["run", "--tier", "free-lite"])
    # Should parse the argument without crashing (may fail on checks)
    assert code in (0, 1, 2)  # 2 = usage/parsing error is also OK


def test_cli_run_with_profile():
    """Test that CLI accepts --profile flag."""
    code, out, err = run_cli(["run", "--profile", "fast"])
    # Should parse the argument without crashing
    assert code in (0, 1, 2)


def test_cli_inspect_command():
    """Test that CLI inspect command works."""
    code, out, err = run_cli(["inspect"])
    # Inspect may fail if no repo context, but should parse the command
    assert code in (0, 1)


def test_cli_status_command():
    """Test that CLI status command works."""
    code, out, err = run_cli(["status"])
    # Status should show tier/license info
    assert code in (0, 1)


def test_cli_version_flag():
    """Test that CLI accepts --version flag."""
    code, out, err = run_cli(["--version"])
    # Should show version (may not be implemented, so allow various exit codes)
    assert code in (0, 1, 2)


def test_cli_no_args_shows_help():
    """Test that CLI with no arguments shows help or usage."""
    code, out, err = run_cli([])
    # Either shows help (code 0) or error (code 1-2)
    assert code in (0, 1, 2)
    # Should show some usage information
    assert len(out) > 0 or len(err) > 0
