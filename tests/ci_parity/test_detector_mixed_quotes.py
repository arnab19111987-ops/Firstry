from firsttry.ci_parity import detector


def test_detect_mixed_quotes(tmp_path, monkeypatch):
    wf = tmp_path / ".github/workflows/ci.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(
        r"""
jobs:
  test:
    steps:
      - run: |
          ruff check --select "E,F,I"
          pytest -q -m 'not slow'
"""
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    ids = [s["id"] for s in d.steps]
    assert ids.count("ruff") == 1
    assert ids.count("pytest") == 1
