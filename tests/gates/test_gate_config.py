from __future__ import annotations

import pathlib
import textwrap

from firsttry.gates.config import load_ci_mirror, load_policy, resolve_jobs_for_gate


def _write(path: pathlib.Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf8")


def test_load_ci_mirror_and_policy(tmp_path: pathlib.Path) -> None:
    ci_toml = """
    [jobs.tests]
    workflow = "ci.yml"
    job_name = "tests"
    tags = ["dev_gate", "merge_gate"]
    plan = "tests_plan"

    [jobs.deploy_prod]
    workflow = "release.yml"
    job_name = "deploy-prod"
    tags = ["release_gate"]
    cloud_only = true

    [plans.tests_plan]
    [[plans.tests_plan.steps]]
    id = "install"
    run = "python -m pip install -e .[ci]"

    [[plans.tests_plan.steps]]
    id = "pytest"
    run = "pytest"
    """

    policy_toml = """
    [gates.dev]
    tags = ["dev_gate"]

    [gates.merge]
    tags = ["dev_gate", "merge_gate"]

    [gates.release]
    tags = ["merge_gate", "release_gate"]
    require_cloud_only_success_in_ci = true
    """

    _write(tmp_path / ".firsttry_ci_mirror.toml", ci_toml)
    _write(tmp_path / ".firsttry_policy.toml", policy_toml)

    ci_cfg = load_ci_mirror(
        root=tmp_path,
        filename=".firsttry_ci_mirror.toml",
    )
    policy = load_policy(
        root=tmp_path,
        filename=".firsttry_policy.toml",
    )

    assert "tests" in ci_cfg.jobs
    assert "deploy_prod" in ci_cfg.jobs
    assert "tests_plan" in ci_cfg.plans

    local_dev, cloud_dev, _ = resolve_jobs_for_gate(ci_cfg, policy, "dev")
    assert [j.name for j in local_dev] == ["tests"]
    assert cloud_dev == []

    local_rel, cloud_rel, _ = resolve_jobs_for_gate(ci_cfg, policy, "release")
    # With the release gate including the merge tag, the `tests` job
    # (tagged with `merge_gate`) is considered part of the release gate
    # and is runnable locally; the deploy job remains cloud-only.
    assert [j.name for j in local_rel] == ["tests"]
    assert [j.name for j in cloud_rel] == ["deploy_prod"]
