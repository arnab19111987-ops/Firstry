import os
import textwrap
from firsttry import ci_mapper


def test_ci_mapper_builds_adaptive_plan(tmp_path):
    # create a fake workflow with custom steps
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf_text = textwrap.dedent(
        """
        name: CustomPipeline
          # typical single-job QA style
        jobs:
          qa:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout
                uses: actions/checkout@v4
              - name: Setup Python
                uses: actions/setup-python@v4
              - name: Install deps
                run: pip install -r requirements.txt
              - name: Lint
                run: ruff check .
              - name: Test
                run: pytest -q
        """
    )
    (wf_dir / "ci.yml").write_text(wf_text, encoding="utf-8")

    plan = ci_mapper.build_ci_plan(str(tmp_path))

    # We expect:
    # - "Checkout" and "Setup Python" are SKIPPED (in SKIP_KEYWORDS)
    # - Install deps, Lint, Test steps remain
    assert "jobs" in plan
    assert len(plan["jobs"]) == 1
    job = plan["jobs"][0]
    assert job["job_name"] == "qa"
    steps = job["steps"]
    names = [s["step_name"] for s in steps]

    assert names == ["Install deps", "Lint", "Test"], names
    assert steps[0]["install"] is True  # pip install marked slow/setup
    assert steps[1]["install"] is False
    assert steps[2]["install"] is False

    # Make sure cmd came through intact
    assert steps[1]["cmd"] == "ruff check ."
    assert steps[2]["cmd"] == "pytest -q"
    # Each step should carry meta info for precise error tracing
    assert "meta" in steps[1]
    assert "workflow" in steps[1]["meta"]
    assert steps[1]["meta"]["workflow"] == "CustomPipeline"
