from firsttry.ci_parity import detector


def test_env_without_src(tmp_path, monkeypatch):
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    assert "PYTHONPATH" not in d.env
