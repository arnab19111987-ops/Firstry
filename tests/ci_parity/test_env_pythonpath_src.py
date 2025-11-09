from firsttry.ci_parity import detector


def test_env_pythonpath_set_when_src_exists(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "src").mkdir()
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    d = detector.detect()
    assert d.env.get("PYTHONPATH") == "src"
