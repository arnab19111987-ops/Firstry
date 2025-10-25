from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

import yaml


@dataclass
class StepPlan:
    name: str
    run: str
    env: Dict[str, str]


@dataclass
class JobPlan:
    job_id: str
    steps: List[StepPlan]


@dataclass
class WorkflowPlan:
    workflow_file: str
    jobs: List[JobPlan]


def _collect_workflow_files(root: Path | str) -> List[Path]:
    """Collect workflow files from root/.github/workflows.

    Args:
        root: Path or string pointing to either the repo root or directly to .github/workflows
    """
    root_path = Path(root) if isinstance(root, str) else root

    # If root already points to .github/workflows, use it directly
    if root_path.name == "workflows" and root_path.parent.name == ".github":
        wf_dir = root_path
    else:
        wf_dir = root_path / ".github" / "workflows"

    if not wf_dir.exists():
        return []
    paths = []
    for p in wf_dir.iterdir():
        if p.suffix in (".yml", ".yaml") and p.is_file():
            paths.append(p)
    return sorted(paths)


def _extract_steps_from_job(job_id: str, job_dict: Dict[str, Any]) -> JobPlan:
    steps_raw = job_dict.get("steps", [])
    steps: List[StepPlan] = []
    job_env = job_dict.get("env", {}) or {}

    for s in steps_raw:
        # skip "uses:" steps like actions/checkout
        run_cmd = s.get("run")
        if not run_cmd:
            continue

        step_env: Dict[str, str] = {}
        step_env.update(job_env)
        step_env.update(s.get("env", {}) or {})

        steps.append(
            StepPlan(
                name=s.get("name", f"step in {job_id}"),
                run=run_cmd,
                env=step_env,
            )
        )
    return JobPlan(job_id=job_id, steps=steps)


def build_ci_plan(root: Path | str) -> Dict[str, Any]:
    """Build a CI plan from GitHub workflows.

    Args:
        root: Path or string pointing to repo root or .github/workflows directory
    """
    workflows: List[WorkflowPlan] = []
    for wf_path in _collect_workflow_files(root):
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8")) or {}
        jobs = data.get("jobs", {}) or {}

        job_plans = []
        for job_id, job_def in jobs.items():
            job_plans.append(_extract_steps_from_job(job_id, job_def))

        workflows.append(
            WorkflowPlan(
                workflow_file=wf_path.name,
                jobs=job_plans,
            )
        )

    return {
        "workflows": [
            {
                "workflow_file": wf.workflow_file,
                "jobs": [
                    {
                        "job_id": j.job_id,
                        "steps": [
                            {
                                "name": st.name,
                                "run": st.run,
                                "env": st.env,
                            }
                            for st in j.steps
                        ],
                    }
                    for j in wf.jobs
                ],
            }
            for wf in workflows
        ]
    }


def rewrite_run_cmd(cmd: str, python_exe: Optional[str] = None) -> str:
    if python_exe is None:
        python_exe = os.environ.get("FIRSTTRY_PYTHON", sys.executable)

    out = cmd

    if "python -m pip" in out:
        out = out.replace("python -m pip", f"{python_exe} -m pip")

    if "pytest" in out and "-m pytest" not in out:
        out = out.replace("pytest", f"{python_exe} -m pytest")

    return out
