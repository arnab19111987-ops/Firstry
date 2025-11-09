from firsttry.ci_parity import planner


def test_build_plan_profiles(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    p_commit = planner.build_plan("pre-commit")
    p_push = planner.build_plan("pre-push")
    p_ci = planner.build_plan("ci")
    assert p_commit.profile == "pre-commit"
    assert p_push.profile == "pre-push"
    assert p_ci.profile == "ci"
    # ci adds packaging probe
    assert any(s.id == "packaging" for s in p_ci.steps)
