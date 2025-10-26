from __future__ import annotations

from click.testing import CliRunner

import firsttry.cli as cli_mod


def test_cli_run_stub_gate_passes():
    runner = CliRunner()
    result = runner.invoke(cli_mod.main, ["run", "--gate", "pre-commit"])

    assert result.exit_code == 0
    assert "FirstTry Gate Summary" in result.output
    assert "SAFE TO COMMIT" in result.output


def test_cli_run_require_license_failure(monkeypatch):
    # Force license check to fail
    monkeypatch.setattr(cli_mod, "assert_license", lambda: (False, [], ""))

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.main, ["run", "--gate", "pre-commit", "--require-license"]
    )

    assert result.exit_code == 1
    assert "License invalid" in result.output


def test_cli_run_require_license_success(monkeypatch):
    # Force license check to pass
    monkeypatch.setattr(cli_mod, "assert_license", lambda: (True, ["basic"], "/tmp/x"))

    runner = CliRunner()
    result = runner.invoke(
        cli_mod.main, ["run", "--gate", "pre-commit", "--require-license"]
    )

    assert result.exit_code == 0
    assert "License ok" in result.output
