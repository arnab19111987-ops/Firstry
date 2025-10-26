from pathlib import Path
import textwrap

from firsttry import ci_mapper_impl as impl


def test_collect_workflow_files_empty(tmp_path: Path):
    # no .github/workflows dir
    out = impl._collect_workflow_files(tmp_path)
    assert out == []


def test_extract_steps_from_job_and_build_plan(tmp_path: Path):
    # create a fake workflow file structure
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    wf = wf_dir / "test.yml"
    wf.write_text(
        textwrap.dedent(
            """
            name: CI
            on: [push]
            jobs:
              build:
                runs-on: ubuntu-latest
                env:
                  GLOBAL: yes
                steps:
                  - uses: actions/checkout@v2
                  - name: Install deps
                    run: python -m pip install -r requirements.txt
                  - name: Run tests
                    run: pytest -q
            """
        ),
        encoding="utf-8",
    )

    plan = impl.build_ci_plan(tmp_path)
    assert "workflows" in plan
    assert len(plan["workflows"]) == 1
    wf_plan = plan["workflows"][0]
    assert wf_plan["workflow_file"] == "test.yml"
    jobs = wf_plan["jobs"]
    assert len(jobs) == 1
    job = jobs[0]
    assert job["job_id"] == "build"
    steps = job["steps"]
    # only the two run steps should be present (uses: step skipped)
    assert any(s["run"].startswith("python -m pip") for s in steps)
    assert any("pytest" in s["run"] for s in steps)


def test_rewrite_run_cmd_replaces_python_and_pytest():
    cmd = "python -m pip install -r requirements.txt && pytest -q"
    out = impl.rewrite_run_cmd(cmd, python_exe="/usr/bin/python3.9")
    assert "/usr/bin/python3.9 -m pip" in out
    assert "/usr/bin/python3.9 -m pytest" in out
