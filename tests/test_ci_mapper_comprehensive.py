import textwrap

from firsttry import ci_mapper


def test_build_ci_plan_multiple_workflows(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    # Create two workflow files
    (wf_dir / "ci.yml").write_text(
        textwrap.dedent(
            """
        name: CI
        jobs:
          test:
            runs-on: ubuntu-latest
            steps:
              - run: pytest
        """,
        ),
        encoding="utf-8",
    )
    (wf_dir / "lint.yml").write_text(
        textwrap.dedent(
            """
        name: Lint
        jobs:
          lint:
            runs-on: ubuntu-latest
            steps:
              - run: ruff check .
        """,
        ),
        encoding="utf-8",
    )

    plan = ci_mapper.build_ci_plan(str(tmp_path))
    assert "jobs" in plan
    assert len(plan["jobs"]) == 2
    job_names = {j["job_name"] for j in plan["jobs"]}
    assert "test" in job_names
    assert "lint" in job_names


def test_build_ci_plan_skip_uses_steps(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    (wf_dir / "test.yml").write_text(
        textwrap.dedent(
            """
        name: Test
        jobs:
          job:
            steps:
              - uses: actions/checkout@v4
              - uses: actions/setup-python@v4
              - run: echo "real step"
        """,
        ),
        encoding="utf-8",
    )

    plan = ci_mapper.build_ci_plan(str(tmp_path))
    # Only the run step should remain
    assert len(plan["jobs"]) == 1
    steps = plan["jobs"][0]["steps"]
    assert len(steps) == 1
    assert "echo" in steps[0]["cmd"]


def test_build_ci_plan_install_hints(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    (wf_dir / "setup.yml").write_text(
        textwrap.dedent(
            """
        name: Setup
        jobs:
          build:
            steps:
              - run: pip install -r requirements.txt
              - run: npm ci
              - run: pytest -q
        """,
        ),
        encoding="utf-8",
    )

    plan = ci_mapper.build_ci_plan(str(tmp_path))
    steps = plan["jobs"][0]["steps"]
    # First two should be marked install=True
    assert steps[0]["install"] is True
    assert steps[1]["install"] is True
    assert steps[2]["install"] is False


def test_rewrite_run_cmd_with_python_exe(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_PYTHON", "/usr/bin/python3.11")
    cmd = "python -m pip install foo && pytest tests/"
    rewritten = ci_mapper.rewrite_run_cmd(cmd)
    assert "/usr/bin/python3.11 -m pip" in rewritten
    assert "/usr/bin/python3.11 -m pytest" in rewritten


def test_rewrite_run_cmd_no_env():
    cmd = "echo hello"
    rewritten = ci_mapper.rewrite_run_cmd(cmd, python_exe=None)
    # Should return unchanged when no python/pytest to replace
    assert rewritten == cmd


def test_looks_like_setup_step():
    from firsttry.ci_mapper import _looks_like_setup_step

    assert _looks_like_setup_step({"run": "pip install -r reqs.txt"}) is True
    assert _looks_like_setup_step({"run": "npm install"}) is True
    assert _looks_like_setup_step({"run": "pytest"}) is False


def test_should_skip_step():
    from firsttry.ci_mapper import _should_skip_step

    assert _should_skip_step({"uses": "actions/checkout@v4"}) is True
    assert _should_skip_step({"uses": "actions/setup-python@v4"}) is True
    assert _should_skip_step({"run": "echo test"}) is False
    assert _should_skip_step({}) is True  # no run or uses


def test_normalize_step():
    from firsttry.ci_mapper import _normalize_step

    step = {"name": "Test", "run": "pytest -q"}
    normalized = _normalize_step(step, "qa", 0, "CI")
    assert normalized is not None
    assert normalized["step_name"] == "Test"
    assert normalized["cmd"] == "pytest -q"
    assert normalized["install"] is False
    assert normalized["meta"]["workflow"] == "CI"


def test_normalize_step_returns_none_for_skipped():
    from firsttry.ci_mapper import _normalize_step

    step = {"uses": "actions/checkout@v4"}
    normalized = _normalize_step(step, "qa", 0, "CI")
    assert normalized is None
