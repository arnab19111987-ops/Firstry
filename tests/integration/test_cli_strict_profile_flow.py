import os

import firsttry.cli as cli


def test_cli_strict_profile_flow(tmp_path, monkeypatch):
    # Create minimal repo files
    (tmp_path / "foo.py").write_text("def test_dummy():\n    assert True\n", encoding="utf-8")

    # Stub run_plan to verify it's called with strict profile
    called = {}

    def fake_run_plan(repo_root, plan, use_remote_cache=True, workers=3):
        called["plan_tasks"] = list(plan.tasks.keys())
        # Build fake result objects used by cmd_run printing
        class R:
            def __init__(self):
                self.status = "ok"
                self.duration_ms = 1
                self.cache_status = "miss-run"

            def to_report_json(self):
                return {"status": "ok"}

        return {k: R() for k in called["plan_tasks"]}

    monkeypatch.setattr(cli, "run_plan", fake_run_plan)

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        code = cli.cmd_run(["strict"])  # strict -> free-strict mapping
    finally:
        os.chdir(cwd)

    assert code == 0
    # Ensure run_plan saw some tasks (mypy/pytest/ruff typically)
    assert called.get("plan_tasks")
