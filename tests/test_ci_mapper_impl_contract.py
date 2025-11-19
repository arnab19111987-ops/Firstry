import importlib

import yaml


def test_rewrite_run_cmd_replacements():
    ci = importlib.import_module("firsttry.ci_mapper_impl")

    cmd = "python -m pip install -r requirements.txt && pytest -q"
    out = ci.rewrite_run_cmd(cmd, python_exe="/usr/bin/python3.11")

    assert "/usr/bin/python3.11 -m pip" in out
    assert "/usr/bin/python3.11 -m pytest" in out


def test_build_ci_plan_parses_workflow(tmp_path):
    # create fake .github/workflows dir
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    wf = {
        "name": "CI",
        "on": ["push"],
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "env": {"A": "1"},
                "steps": [
                    {"uses": "actions/checkout@v2"},
                    {
                        "name": "Install",
                        "run": "python -m pip install -r requirements.txt",
                        "env": {"B": "2"},
                    },
                    {"name": "Test", "run": "pytest -q"},
                ],
            }
        },
    }

    wf_path = wf_dir / "ci.yml"
    wf_path.write_text(yaml.safe_dump(wf), encoding="utf-8")

    ci = importlib.import_module("firsttry.ci_mapper_impl")

    plan = ci.build_ci_plan(tmp_path)

    assert "workflows" in plan
    assert any(w.get("workflow_file") == "ci.yml" for w in plan["workflows"])
    # find the build job and its steps
    wf_entry = next(w for w in plan["workflows"] if w["workflow_file"] == "ci.yml")
    assert any(j["job_id"] == "build" for j in wf_entry["jobs"])
    build_job = next(j for j in wf_entry["jobs"] if j["job_id"] == "build")
    # Only steps with 'run' should be present (uses steps get skipped)
    step_runs = [s["run"] for s in build_job["steps"]]
    assert any("pip install" in r for r in step_runs)
    assert any("pytest" in r for r in step_runs)
