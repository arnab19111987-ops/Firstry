import types

from click.testing import CliRunner

import firsttry.cli as cli


def test_cli_aborts_without_license(monkeypatch):
    # Force require_license=True path and return invalid
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "")
    monkeypatch.setenv("FIRSTTRY_LICENSE_URL", "")
    # stub runners so they won't run
    ok = types.SimpleNamespace(
        ok=True,
        name="ok",
        duration_s=0.0,
        stdout="",
        stderr="",
        cmd=("x",),
    )
    monkeypatch.setattr("firsttry.cli.runners.run_ruff", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_black_check", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_mypy", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_pytest_kexpr", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_coverage_xml", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.coverage_gate", lambda *a, **k: ok)

    res = CliRunner().invoke(cli.cli_app, ["run", "--gate", "pre-commit", "--require-license"])
    assert res.exit_code != 0
    assert "Tier 'pro' is locked" in res.output or "License invalid" in res.output
    assert "FIRSTTRY_LICENSE_KEY" in res.output
