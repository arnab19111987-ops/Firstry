from pathlib import Path

from firsttry.ci_parity import detector


def write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_detect_from_actions_yaml(tmp_path, monkeypatch):
    repo = tmp_path
    wf = repo / ".github" / "workflows" / "ci.yml"
    write(
        wf,
        """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: |
          pip install -e .[test]
          black --check src tests
          ruff check --select ALL
          pytest -q -m "not slow"
    """,
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    d = detector.detect()
    ids = [s["id"] for s in d.steps]
    assert "black" in ids
    assert "ruff" in ids
    assert "pytest" in ids
    # env includes PYTHONPATH=src only if src exists; absent by default
    assert isinstance(d.env, dict)
