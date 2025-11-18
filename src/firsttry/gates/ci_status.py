from __future__ import annotations

import json
import os
import pathlib
from typing import Dict, Literal, Optional

from .config import Job

Status = Literal["unknown", "pass", "fail"]


def _load_status_file(path: pathlib.Path) -> Dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf8"))
    except Exception:
        return {}
    jobs = data.get("jobs") or {}
    if not isinstance(jobs, dict):
        return {}
    result: Dict[str, str] = {}
    for k, v in jobs.items():
        if isinstance(k, str) and isinstance(v, str):
            if v.lower() in {"pass", "fail"}:
                result[k] = v.lower()
    return result


def _job_key(job: Job) -> str:
    # must match what discovery uses ("workflow:job_id")
    wf = job.workflow or "?"
    jn = job.job_name or job.name
    return f"{wf}:{jn}"


def get_cloud_job_statuses(
    jobs: list[Job],
    *,
    root: Optional[pathlib.Path] = None,
    filename: str = ".firsttry/ci_status.json",
) -> Dict[str, Status]:
    root = root or pathlib.Path(os.getcwd())
    path = root / filename
    if not path.is_file():
        return {job.name: "unknown" for job in jobs}

    raw = _load_status_file(path)
    result: Dict[str, Status] = {}
    for job in jobs:
        key = _job_key(job)
        v = raw.get(key)
        if v == "pass":
            result[job.name] = "pass"
        elif v == "fail":
            result[job.name] = "fail"
        else:
            result[job.name] = "unknown"
    return result
