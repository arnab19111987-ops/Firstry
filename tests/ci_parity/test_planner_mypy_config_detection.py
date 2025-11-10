from pathlib import Path
import os
from firsttry.ci_parity import planner


def test_mypy_uses_repo_config(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("x=1\n")
    (repo / "mypy.ini").write_text("[mypy]\npython_version = 3.11\n")

    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    plan = planner.build_plan("ci")
    mypy_steps = [s for s in plan.steps if s.id.startswith("mypy")]
    assert mypy_steps, "expected at least one mypy step"
    cmd = mypy_steps[0].cmd
    assert any("--config-file=mypy.ini" in c for c in cmd), cmd


def test_mypy_strict_env_override(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("x=1\n")
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    monkeypatch.setenv("FT_MYPY_STRICT", "1")
    plan = planner.build_plan("ci")
    mypy_steps = [s for s in plan.steps if s.id.startswith("mypy")]
    cmd = mypy_steps[0].cmd
    assert "--strict" in cmd, cmd
