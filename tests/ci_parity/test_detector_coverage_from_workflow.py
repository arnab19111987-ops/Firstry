from firsttry.ci_parity import detector


def test_detect_coverage_threshold_from_workflow(tmp_path, monkeypatch):
    wf = tmp_path / ".github/workflows/ci.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(
        """
jobs:
  test:
    steps:
      - run: pytest -q --cov=src --cov-branch --cov-fail-under=87
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    ids = [s["id"] for s in d.steps]
    assert "pytest" in ids
    assert any(s.get("id") == "coverage-threshold" and s.get("threshold") == 87 for s in d.steps)
