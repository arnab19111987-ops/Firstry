from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List

import yaml

from firsttry.ci_discovery.model import CIJob


def discover_ci_jobs(workflows_dir: str = ".github/workflows") -> List[CIJob]:
    """Discover CI jobs by scanning workflow YAML files.

    This is a lightweight discovery: it reads each workflow YAML and
    extracts top-level `jobs` keys into `CIJob` objects.
    """
    jobs: List[CIJob] = []
    base = Path(workflows_dir)
    if not base.exists():
        return jobs

    for path in glob.glob(os.path.join(workflows_dir, "*.yml")) + glob.glob(
        os.path.join(workflows_dir, "*.yaml")
    ):
        try:
            with open(path, "r") as f:
                doc = yaml.safe_load(f)
        except Exception:
            continue

        wf_name = Path(path).stem
        if not isinstance(doc, dict):
            continue

        jobs_map = doc.get("jobs", {}) or {}
        for job_id, job_def in jobs_map.items():
            job_name = job_def.get("name") or job_id
            uses = False
            run_cmds = []
            # Inspect steps to heuristically detect commands
            for step in job_def.get("steps", []) if isinstance(job_def.get("steps", []), list) else []:
                if isinstance(step, dict):
                    if step.get("uses"):
                        uses = True
                    if step.get("run"):
                        run_cmds.append(step.get("run"))

            jobs.append(CIJob(workflow=wf_name, job_id=job_id, job_name=job_name, uses_actions=uses, run_commands=run_cmds))

    return jobs


__all__ = ["discover_ci_jobs"]
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from ..ci_discovery.model import CIJob


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
