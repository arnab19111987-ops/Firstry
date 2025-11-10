from firsttry.ci_parity import planner


def test_apply_scope_staged_files(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "a.py").write_text("x=1")
    (repo / "tests" / "t.py").write_text("def test_x(): pass")

    # fake staged files
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    monkeypatch.setattr("firsttry.ci_parity.util.staged_or_changed_paths", lambda: ["src/a.py"])
    plan = planner.build_plan("pre-commit")
    # Expect black/ruff/mypy cmds to include src/a.py
    cmds = {s.id: s.cmd for s in plan.steps}
    for k in ("black", "ruff", "mypy"):
        if k in cmds:
            assert "src/a.py" in cmds[k]
