from __future__ import annotations

from firsttry.gates.config import Job
from firsttry.gates.runner import GateRun


def test_gate_run_ok_respects_cloud_only_failures() -> None:
    dummy_job = Job(
        name="ci.yml:deploy-prod",
        workflow="ci.yml",
        job_name="deploy-prod",
        tags=["release_gate"],
        plan=None,
        cloud_only=True,
    )
    gr = GateRun(
        gate="release",  # type: ignore[arg-type]
        local_results=[],
        cloud_only_jobs=[dummy_job],
        unmatched_jobs=[],
        started_at=0.0,
        ended_at=1.0,
        require_cloud_only_success_in_ci=True,
        cloud_only_failed_jobs=[dummy_job],
    )
    assert gr.ok is False

    gr2 = GateRun(
        gate="release",  # type: ignore[arg-type]
        local_results=[],
        cloud_only_jobs=[dummy_job],
        unmatched_jobs=[],
        started_at=0.0,
        ended_at=1.0,
        require_cloud_only_success_in_ci=True,
        cloud_only_failed_jobs=[],
    )
    assert gr2.ok is True
