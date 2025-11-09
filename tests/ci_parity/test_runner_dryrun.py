from firsttry.ci_parity import runner


def test_runner_dryrun(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    (tmp_path / "tests").mkdir()
    monkeypatch.setenv("FT_CI_PARITY_DRYRUN", "1")
    rc = runner.main(["pre-commit"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[dryrun]" in out
