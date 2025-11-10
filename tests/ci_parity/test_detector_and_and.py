from firsttry.ci_parity import detector


def test_detect_singleline_with_and(tmp_path, monkeypatch):
    wf = tmp_path / ".github/workflows/ci.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(
        """
jobs:
  lint:
    steps:
      - run: black --check src && ruff check && python -m pytest -q
"""
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    ids = {s["id"] for s in d.steps}
    assert {"black", "ruff", "pytest"}.issubset(ids)
