from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from firsttry.ci_discovery.model import CIJob


def _collect_job_info(workflow_name: str, job_id: str, job_def: dict) -> CIJob:
    job_name = job_def.get("name") or job_id
    steps = job_def.get("steps", []) or []

    uses_actions: List[str] = []
    run_commands: List[str] = []

    for s in steps:
        if isinstance(s, dict):
            if "uses" in s:
                uses_actions.append(str(s.get("uses")))
            if "run" in s:
                run_commands.append(str(s.get("run")))

    return CIJob(
        workflow=workflow_name,
        job_id=job_id,
        job_name=job_name,
        uses_actions=uses_actions,
        run_commands=run_commands,
    )


def discover_ci_jobs(root: Path | None = None) -> List[CIJob]:
    root = root or Path(".github/workflows")
    jobs: List[CIJob] = []

    if not root.exists() or not root.is_dir():
        return jobs

    for wf in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        try:
            doc = yaml.safe_load(wf.read_text()) or {}
        except Exception:
            # Skip unparsable workflow files
            continue

        workflow_name = wf.stem

        wf_jobs = doc.get("jobs") or {}
        if not isinstance(wf_jobs, dict):
            continue

        for job_id, job_def in wf_jobs.items():
            if not isinstance(job_def, dict):
                continue
            jobs.append(_collect_job_info(workflow_name, job_id, job_def))

    return jobs


__all__ = ["discover_ci_jobs", "_collect_job_info"]
