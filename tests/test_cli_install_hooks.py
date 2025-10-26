from click.testing import CliRunner

import firsttry.cli as cli_mod


def test_cli_install_hooks(monkeypatch, tmp_path):
    p1 = tmp_path / "pre-commit"
    p2 = tmp_path / "pre-push"

    def fake_install_git_hooks():
        return str(p1), str(p2)

    monkeypatch.setattr("firsttry.cli.install_git_hooks", fake_install_git_hooks)

    runner = CliRunner()
    res = runner.invoke(cli_mod.main, ["install-hooks"])

    assert res.exit_code == 0
    out = res.output
    assert str(p1) in out and str(p2) in out
