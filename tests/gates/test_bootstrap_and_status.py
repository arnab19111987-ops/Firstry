from __future__ import annotations

import json
import pathlib

from firsttry.gates.bootstrap import ensure_ci_mirror_exists, ensure_policy_exists
from firsttry.gates.ci_status import get_cloud_job_statuses
from firsttry.gates.config import Job


def test_bootstrap_creates_policy_and_ci_mirror(tmp_path: pathlib.Path) -> None:
    policy_path = ensure_policy_exists(root=tmp_path)
    ci_path = ensure_ci_mirror_exists(root=tmp_path)

    assert policy_path.is_file()
    assert ci_path.is_file()

    policy_text = policy_path.read_text(encoding="utf8")
    assert "[gates.dev]" in policy_text
    assert "[gates.release]" in policy_text

    ci_text = ci_path.read_text(encoding="utf8")
    assert "[jobs." in ci_text
    assert "[plans." in ci_text


def test_ci_status_reads_json_and_marks_unknown(tmp_path: pathlib.Path) -> None:
    # create a dummy status file
    status_path = tmp_path / ".firsttry" / "ci_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "jobs": {
            "ci.yml:deploy-prod": "fail",
            "ci.yml:tests": "pass",
        }
    }
    status_path.write_text(json.dumps(data), encoding="utf8")

    jobs = [
        Job(
            name="ci.yml:tests",
            workflow="ci.yml",
            job_name="tests",
            tags=[],
            plan=None,
            cloud_only=True,
        ),
        Job(
            name="ci.yml:deploy-prod",
            workflow="ci.yml",
            job_name="deploy-prod",
            tags=[],
            plan=None,
            cloud_only=True,
        ),
        Job(
            name="ci.yml:other",
            workflow="ci.yml",
            job_name="other",
            tags=[],
            plan=None,
            cloud_only=True,
        ),
    ]

    statuses = get_cloud_job_statuses(jobs, root=tmp_path)
    assert statuses["ci.yml:tests"] == "pass"
    assert statuses["ci.yml:deploy-prod"] == "fail"
    assert statuses["ci.yml:other"] == "unknown"
