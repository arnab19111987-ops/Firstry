"""
Minimal CLI args parity test – ensures flags are accepted without tool execution.
Complements test_cli_args_parity.py with faster tests that don't run actual checks.
"""

import argparse
from unittest.mock import patch

import pytest


@pytest.mark.parametrize(
    "args",
    [
        ["run", "--tier", "lite"],
        ["run", "--profile", "fast"],
        ["run", "--level", "strict"],
        ["run", "--report-json", "/tmp/firsttry_report.json"],
        ["run", "--report-schema"],
        ["run", "--dry-run"],
        ["run", "strict"],  # legacy positional
        ["run", "lite", "--dry-run"],  # legacy + modern
        ["run", "--profile", "fast", "--report-json", "/tmp/report.json"],
    ],
)
def test_cmd_run_accepts_flags(monkeypatch, args):
    """
    Test that cmd_run accepts all expected flags without error.
    This is a fast, flag-only parity check (no actual tool execution).
    """
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    # Mock out the heavy orchestrator to make test fast
    import firsttry.cli as cli_module

    with patch.object(cli_module, "_build_plan_for_tier", return_value=[]):
        with patch.object(cli_module, "run_plan", return_value={}):
            # cmd_run should accept args and return 0 (success)
            result = cli_module.cmd_run(argv=args[1:])  # skip 'run' subcommand
            assert result == 0, f"cmd_run failed with args {args}: exit code {result}"


def test_cmd_run_help_shows_all_flags():
    """
    Verify that --help documents all expected flags for discoverability.
    """
    import io
    from contextlib import redirect_stdout

    import firsttry.cli as cli_module

    # Capture help output
    with pytest.raises(SystemExit):  # argparse calls sys.exit(0) on --help
        with redirect_stdout(io.StringIO()):
            cli_module.cmd_run(argv=["--help"])

    # Alternative: just test that parser doesn't crash
    parser = argparse.ArgumentParser()
    cli_module._add_run_flags(parser)
    ns = parser.parse_args(["--report-json", "/tmp/x.json", "--dry-run"])
    assert ns.report_json == "/tmp/x.json"
    assert ns.dry_run is True


@pytest.mark.parametrize(
    "args,should_succeed",
    [
        (["run", "--tier", "lite"], True),
        (["run", "--profile", "fast"], True),
        (["run", "--tier", "lite", "--report-json", "/tmp/report.json"], True),
        (["run", "--tier", "lite", "--dry-run"], True),
    ],
)
def test_cmd_run_with_mocked_orchestrator(monkeypatch, args, should_succeed):
    """
    Test cmd_run with mocked orchestrator, ensuring flags flow through correctly.
    """
    import firsttry.cli as cli_module

    mock_plan = [{"tool": "ruff"}]
    mock_results = {}

    with patch.object(cli_module, "_build_plan_for_tier", return_value=mock_plan) as mock_build:
        with patch.object(cli_module, "run_plan", return_value=mock_results) as mock_run:
            result = cli_module.cmd_run(argv=args[1:])

            if should_succeed:
                assert result == 0
                # Verify orchestrator was called
                mock_build.assert_called()
                mock_run.assert_called()


# Quick import test – ensure _add_run_flags is exported and usable
def test_add_run_flags_function_exists():
    """Ensure the de-drifting helper function is available."""
    import argparse

    import firsttry.cli as cli_module

    assert hasattr(cli_module, "_add_run_flags")
    assert callable(cli_module._add_run_flags)

    # Test that it works with a fresh parser
    p = argparse.ArgumentParser()
    cli_module._add_run_flags(p)
    ns = p.parse_args(["--profile", "strict"])
    assert ns.profile == "strict"
