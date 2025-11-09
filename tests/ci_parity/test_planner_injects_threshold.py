from firsttry.ci_parity import planner


def test_planner_injects_threshold(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text(
        """
jobs:
  test:
    steps:
      - run: pytest -q --cov=src --cov-fail-under=90
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    plan = planner.build_plan("ci")
    py = next(s for s in plan.steps if s.id == "pytest")
    assert any(a.startswith("--cov-fail-under=") for a in py.cmd)
    assert any("90" in a for a in py.cmd if a.startswith("--cov-fail-under="))
