import types

from click.testing import CliRunner

from firsttry.cli import main


def test_cli_runs_and_summarizes(monkeypatch, tmp_path):
    # prevent real subprocess calls by stubbing runner functions
    fake_ok = types.SimpleNamespace(
        ok=True,
        name="fake",
        duration_s=0.01,
        stdout="ok",
        stderr="",
        cmd=("x",),
    )

    def ok_step(*a, **k):
        return fake_ok

    monkeypatch.setattr(
        "firsttry.cli.install_pre_commit_hook",
        lambda *a, **k: tmp_path / "pc",
    )
    monkeypatch.setattr(
        "firsttry.cli.get_changed_files",
        lambda *a, **k: ["tools/firsttry/firsttry/cli.py"],
    )
    monkeypatch.setattr("firsttry.cli.runners.run_ruff", ok_step)
    monkeypatch.setattr("firsttry.cli.runners.run_black_check", ok_step)
    monkeypatch.setattr("firsttry.cli.runners.run_mypy", ok_step)
    monkeypatch.setattr("firsttry.cli.runners.run_pytest_kexpr", ok_step)
    monkeypatch.setattr("firsttry.cli.runners.run_coverage_xml", ok_step)
    monkeypatch.setattr("firsttry.cli.runners.coverage_gate", ok_step)

    runner = CliRunner()
    res = runner.invoke(main, ["run", "--gate", "pre-commit"])
    assert res.exit_code == 0
    assert "Gate Summary" in res.output
