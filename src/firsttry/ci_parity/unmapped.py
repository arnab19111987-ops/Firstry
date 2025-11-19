"""Detect unmapped CI jobs/steps and provide a simple API for gate reporting.

This module is intentionally lightweight: it re-uses the existing workflow
parsing utilities and reports a flat list of UnmappedStep entries which
the gate summary builder can consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from .intents import (
    DEFAULT_MIRROR_PATH,
    DEFAULT_WORKFLOWS_ROOT,
    _iter_workflow_files,
    _load_mirror_jobs,
)


@dataclass(frozen=True)
class UnmappedStep:
    workflow: str
    job: str
    step: str
    reason: str


def find_unmapped_steps(
    mirror_path: Optional[str | Path] = None,
    workflows_root: Optional[str | Path] = None,
) -> List[UnmappedStep]:
    """Return a flat list of UnmappedStep found by comparing workflows to the mirror.

    This is intentionally conservative: it reports jobs that are missing from the
    mirror, any declared `services` in a job (service containers), and `uses`
    actions referenced from job steps so callers can inspect unknown actions.
    """
    mpath = Path(mirror_path) if mirror_path is not None else DEFAULT_MIRROR_PATH
    wroot = (
        Path(workflows_root) if workflows_root is not None else DEFAULT_WORKFLOWS_ROOT
    )

    try:
        mirror_jobs = _load_mirror_jobs(mpath)
    except Exception:
        mirror_jobs = []

    mirror_index = {(mj.workflow, mj.job_id) for mj in mirror_jobs}

    results: List[UnmappedStep] = []

    for wf_path in _iter_workflow_files(wroot):
        try:
            data = yaml.safe_load(wf_path.read_text()) or {}
        except Exception:
            # If parsing fails, surface it as an unmapped/workflow issue
            results.append(
                UnmappedStep(
                    workflow=wf_path.name,
                    job="<workflow-parse-error>",
                    step="<parsing>",
                    reason="failed to parse workflow",
                )
            )
            continue

        wf_name = wf_path.name
        wf_jobs = (data or {}).get("jobs") or {}
        if not isinstance(wf_jobs, dict):
            continue

        for job_id, job_def in wf_jobs.items():
            key = (wf_name, job_id)
            # If the job is entirely missing from the mirror, report it
            if key not in mirror_index:
                results.append(
                    UnmappedStep(
                        workflow=wf_name,
                        job=job_id,
                        step="<job>",
                        reason="missing mirror mapping",
                    )
                )

            # If the job declares service containers, surface them
            if isinstance(job_def, dict):
                services = job_def.get("services")
                if services:
                    results.append(
                        UnmappedStep(
                            workflow=wf_name,
                            job=job_id,
                            step="services",
                            reason="service container(s) declared",
                        )
                    )

                steps = job_def.get("steps") or []
                if isinstance(steps, list):
                    for step in steps:
                        if not isinstance(step, dict):
                            continue
                        if "uses" in step:
                            uses = step.get("uses")
                            if isinstance(uses, str):
                                results.append(
                                    UnmappedStep(
                                        workflow=wf_name,
                                        job=job_id,
                                        step=uses,
                                        reason=f"action referenced: {uses}",
                                    )
                                )

    return results


def get_unmapped_steps_for_gate(
    gate_name: str,
    mirror_path: Optional[str | Path] = None,
    workflows_root: Optional[str | Path] = None,
) -> List[UnmappedStep]:
    """Return unmapped steps relevant for a gate.

    Currently this returns all unmapped steps across workflows; future
    enhancements can filter by gate_name to include only gate-relevant
    workflows.
    """
    return find_unmapped_steps(mirror_path=mirror_path, workflows_root=workflows_root)
