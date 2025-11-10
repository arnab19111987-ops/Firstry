from __future__ import annotations

import toml
from pathlib import Path
from typing import Dict, List, Set


def load_mirror_config(path: str = ".firsttry/ci_mirror.toml") -> Dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = toml.loads(p.read_text())
    except Exception:
        return {}

    # Expect format: { ["workflow/job"] = "mapped-name" }
    mapping: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(v, str):
            mapping[k] = v
    return mapping


def find_unmapped_ci_jobs(discovered: List[object], mapping: Dict[str, str]) -> Set[str]:
    """Return set of discovered job keys not present in mapping.

    A discovered job is keyed as `workflow/job_id` to match the mapping file.
    """
    missing: Set[str] = set()
    for job in discovered:
        key = f"{job.workflow}/{job.job_id}"
        if key not in mapping:
            missing.add(key)
    return missing


__all__ = ["load_mirror_config", "find_unmapped_ci_jobs"]
from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Any, List

import toml

from ..ci_discovery.reader import discover_ci_jobs
from ..ci_discovery.model import CIJob


def load_mirror_config(path: Path | None = None) -> Dict[str, Any]:
    path = path or Path(".firsttry/ci_mirror.toml")
    if not path.exists():
        return {}
    try:
        return toml.loads(path.read_text())
    except Exception:
        return {}


def get_mapped_ci_job_ids(config: Dict[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    jobs = config.get("job") or {}
    for key, v in jobs.items():
        if isinstance(v, dict):
            ci_job = v.get("ci_job")
            if isinstance(ci_job, str):
                ids.add(ci_job)
    return ids


def find_unmapped_ci_jobs(root: Path | None = None, config_path: Path | None = None) -> List[CIJob]:
    config = load_mirror_config(config_path)
    mapped = get_mapped_ci_job_ids(config)

    discovered = discover_ci_jobs(root)
    unmapped: List[CIJob] = []
    for j in discovered:
        if j.job_id not in mapped:
            unmapped.append(j)
    return unmapped


__all__ = ["load_mirror_config", "get_mapped_ci_job_ids", "find_unmapped_ci_jobs"]
