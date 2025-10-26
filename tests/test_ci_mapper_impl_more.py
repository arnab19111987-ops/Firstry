import textwrap
from firsttry import ci_mapper_impl as impl


def test_impl_collect_when_root_is_workflows_dir(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "x.yml").write_text(
        textwrap.dedent(
            """
            name: W
            jobs:
              j:
                steps:
                  - name: Echo
                    run: echo hi
            """
        ),
        encoding="utf-8",
    )

    plan1 = impl.build_ci_plan(tmp_path)
    plan2 = impl.build_ci_plan(workflows)

    assert plan1["workflows"][0]["workflow_file"] == "x.yml"
    assert plan2["workflows"][0]["workflow_file"] == "x.yml"
