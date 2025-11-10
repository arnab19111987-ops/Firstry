from pathlib import Path

from firsttry.ci_parity import detector


def write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_detect_multi_job_and_singleline(tmp_path, monkeypatch):
    repo = tmp_path
    wf = repo / ".github" / "workflows" / "ci.yml"
    write(
        wf,
        """
name: CI
on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: black --check src tests
      - run: ruff check
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python -m pytest -q
""",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    d = detector.detect()
    ids = {s["id"] for s in d.steps}
    assert {"black", "ruff", "pytest"}.issubset(ids)
