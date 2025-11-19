from firsttry.ci_mapper_impl import (
    _collect_workflow_files,
    _extract_steps_from_job,
    build_ci_plan,
    rewrite_run_cmd,
)


def test_collect_workflow_files_from_workflows_dir(tmp_path):
    # Test passing .github/workflows directly
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "a.yml").write_text("name: A", encoding="utf-8")
    (wf_dir / "b.yaml").write_text("name: B", encoding="utf-8")
    (wf_dir / "readme.md").write_text("# ignore", encoding="utf-8")

    files = _collect_workflow_files(wf_dir)
    assert len(files) == 2
    names = {f.name for f in files}
    assert "a.yml" in names
    assert "b.yaml" in names


def test_collect_workflow_files_nonexistent(tmp_path):
    files = _collect_workflow_files(tmp_path / "nonexistent")
    assert files == []


def test_extract_steps_from_job_with_env():
    job_dict = {
        "env": {"GLOBAL": "1"},
        "steps": [
            {"name": "Setup", "run": "echo setup", "env": {"LOCAL": "2"}},
            {"name": "Test", "run": "pytest"},
        ],
    }
    job_plan = _extract_steps_from_job("test_job", job_dict)
    assert job_plan.job_id == "test_job"
    assert len(job_plan.steps) == 2

    # First step should have both GLOBAL and LOCAL
    assert job_plan.steps[0].env["GLOBAL"] == "1"
    assert job_plan.steps[0].env["LOCAL"] == "2"

    # Second step should have only GLOBAL
    assert job_plan.steps[1].env["GLOBAL"] == "1"
    assert "LOCAL" not in job_plan.steps[1].env


def test_extract_steps_skips_uses_only():
    job_dict = {
        "steps": [
            {"uses": "actions/checkout@v4"},
            {"name": "Real", "run": "echo hi"},
        ]
    }
    job_plan = _extract_steps_from_job("job", job_dict)
    # Should only extract the run step
    assert len(job_plan.steps) == 1
    assert job_plan.steps[0].name == "Real"


def test_build_ci_plan_no_jobs(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "empty.yml").write_text("name: Empty\n", encoding="utf-8")

    plan = build_ci_plan(tmp_path)
    # Empty workflow is still included with empty jobs list
    assert "workflows" in plan
    assert len(plan["workflows"]) == 1
    assert plan["workflows"][0]["jobs"] == []


def test_rewrite_run_cmd_python_and_pytest():
    cmd = "python -m pip install foo && pytest -q"
    rewritten = rewrite_run_cmd(cmd, python_exe="/opt/python3.10")
    assert "/opt/python3.10 -m pip" in rewritten
    assert "/opt/python3.10 -m pytest" in rewritten


def test_rewrite_run_cmd_no_python_exe():
    import os

    # Clear env
    old = os.environ.pop("FIRSTTRY_PYTHON", None)
    try:
        cmd = "echo test"
        rewritten = rewrite_run_cmd(cmd, python_exe=None)
        # Should use sys.executable by default, but for 'echo' no substitution
        assert "echo test" in rewritten
    finally:
        if old:
            os.environ["FIRSTTRY_PYTHON"] = old
