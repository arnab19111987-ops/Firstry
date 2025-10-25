import textwrap
from firsttry.ci_mapper import build_ci_plan, rewrite_run_cmd


def test_build_ci_plan_basic(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    yaml_text = textwrap.dedent(
        """
        name: CI
        on: [push]
        jobs:
          test:
            runs-on: ubuntu-latest
            env:
              GLOBAL_FLAG: "1"
            steps:
              - uses: actions/checkout@v4
              - name: Install deps
                run: python -m pip install -r requirements.txt
                env:
                  EXTRA_FLAG: "yes"
              - name: Run pytest
                run: pytest -q
        """
    )
    (wf_dir / "ci.yml").write_text(yaml_text, encoding="utf-8")

    plan = build_ci_plan(tmp_path)

    assert "workflows" in plan
    assert len(plan["workflows"]) == 1
    wf = plan["workflows"][0]
    assert wf["workflow_file"] == "ci.yml"
    assert len(wf["jobs"]) == 1
    job = wf["jobs"][0]
    assert job["job_id"] == "test"

    steps = job["steps"]
    assert len(steps) == 2

    step0 = steps[0]
    assert step0["name"] == "Install deps"
    assert "python -m pip install" in step0["run"]
    assert step0["env"]["GLOBAL_FLAG"] == "1"
    assert step0["env"]["EXTRA_FLAG"] == "yes"

    step1 = steps[1]
    assert "pytest -q" in step1["run"]
    assert step1["env"]["GLOBAL_FLAG"] == "1"


def test_rewrite_run_cmd_substitutions(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_PYTHON", "/custom/python")
    out = rewrite_run_cmd("python -m pip install -r reqs.txt && pytest -q")
    assert out.startswith("/custom/python -m pip install")
    assert "/custom/python -m pytest -q" in out
