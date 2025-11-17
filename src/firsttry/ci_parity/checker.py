from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import toml


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
