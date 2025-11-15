import os
from types import SimpleNamespace

import firsttry.cli as cli


def test_cli_run_free_tier_happy_path(tmp_path, monkeypatch):
    # 1) Minimal repo structure
    (tmp_path / "foo.py").write_text("def test_dummy():\n    assert True\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.firsttry]\nci = 'github-actions'\n",
        encoding="utf-8",
    )

    # 2) Stub out the expensive run_plan to return minimal results
    def fake_run_plan(repo_root, plan, use_remote_cache=True, workers=3):
        r = SimpleNamespace()
        r.status = "ok"
        r.duration_ms = 10
        r.cache_status = "hit-local"
        r.to_report_json = lambda: {"status": "ok"}
        return {"ruff": r, "pytest": r}

    monkeypatch.setenv("FIRSTTRY_TIER", "free-lite")
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "")
    monkeypatch.setenv("FT_SEND_TELEMETRY", "0")

    monkeypatch.setattr(cli, "run_plan", fake_run_plan)

    # 3) Run the main run path in-process
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        code = cli.cmd_run(["fast"])  # fast -> free-lite
    finally:
        os.chdir(cwd)

    # 4) Assert it did not blow up
    assert code == 0
    # Report file should be written
    report_path = tmp_path / ".firsttry" / "report.json"
    assert report_path.exists()
