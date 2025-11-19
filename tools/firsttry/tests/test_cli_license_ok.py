import types

from click.testing import CliRunner

from firsttry.cli import main


def test_cli_runs_when_license_ok(monkeypatch):
    # Make license checker return ok & features
    monkeypatch.setattr(
        "firsttry.cli.assert_license", lambda: (True, ["featX"], "cache")
    )

    # Stub all runners to OK so the CLI completes with exit 0
    ok = types.SimpleNamespace(
        ok=True, name="ok", duration_s=0.0, stdout="", stderr="", cmd=("x",)
    )
    monkeypatch.setattr("firsttry.cli.runners.run_ruff", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_black_check", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_mypy", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_pytest_kexpr", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.run_coverage_xml", lambda *a, **k: ok)
    monkeypatch.setattr("firsttry.cli.runners.coverage_gate", lambda *a, **k: ok)

    res = CliRunner().invoke(main, ["run", "--gate", "pre-commit", "--require-license"])
    assert res.exit_code == 0
    assert "License ok" in res.output
