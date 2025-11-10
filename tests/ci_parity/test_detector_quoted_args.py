from firsttry.ci_parity import detector


def test_detect_with_quoted_args(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/ci.yml").write_text(
        """
jobs:
  test:
    steps:
      - run: |
          ruff check --select "E,F,I"
          black --check "src tests"
          pytest -q -m "not slow"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    d = detector.detect()
    ids = [s["id"] for s in d.steps]
    assert ids.count("black") == 1
    assert ids.count("ruff") == 1
    assert ids.count("pytest") == 1
