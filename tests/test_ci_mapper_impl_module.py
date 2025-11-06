import textwrap

from firsttry.ci_mapper_impl import build_ci_plan
from firsttry.ci_mapper_impl import rewrite_run_cmd


def test_ci_mapper_impl_build_plan_with_env_inheritance(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    yaml_text = textwrap.dedent(
        """
        name: ImplCI
        on: [push]
        jobs:
          pkg:
            runs-on: ubuntu-latest
            env:
              TOP: "A"
            steps:
              - uses: actions/checkout@v4
              - name: Install
                run: python -m pip install -r requirements.txt
                env:
                  MID: "B"
              - name: Test
                run: pytest -q
        """,
    )
    (wf_dir / "ci.yml").write_text(yaml_text, encoding="utf-8")

    plan = build_ci_plan(tmp_path)

    assert "workflows" in plan
    assert len(plan["workflows"]) == 1
    wf = plan["workflows"][0]
    assert wf["workflow_file"] == "ci.yml"

    assert len(wf["jobs"]) == 1
    job = wf["jobs"][0]
    assert job["job_id"] == "pkg"

    steps = job["steps"]
    assert [s["name"] for s in steps] == ["Install", "Test"]

    # env inheritance: job-level + step-level
    s0 = steps[0]
    assert "python -m pip install" in s0["run"]
    assert s0["env"]["TOP"] == "A"
    assert s0["env"]["MID"] == "B"

    s1 = steps[1]
    assert "pytest -q" in s1["run"]
    assert s1["env"]["TOP"] == "A"


def test_ci_mapper_impl_rewrite_cmd(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_PYTHON", "/opt/py")
    out = rewrite_run_cmd("python -m pip install -r reqs.txt && pytest -q")
    assert out.startswith("/opt/py -m pip install")
    assert "/opt/py -m pytest -q" in out
