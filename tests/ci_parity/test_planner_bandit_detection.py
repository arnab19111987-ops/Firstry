from firsttry.ci_parity import planner


def test_bandit_added_when_seen_in_workflow(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text(
        """
jobs:
  sec:
    steps:
      - run: bandit -q -r src
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    p = planner.build_plan("ci")
    assert any(s.id == "bandit" for s in p.steps)
