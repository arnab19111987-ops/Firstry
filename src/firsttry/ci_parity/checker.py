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

    # Build a mapping of CI job_id -> mirror-name by scanning the parsed TOML
    # for any table that contains a `ci_job` key. This supports older simple
    # formats and the current `[job.<name>]` style used in `.firsttry/ci_mirror.toml`.
    mapping: Dict[str, str] = {}

    def _walk(d: dict, prefix: str | None = None) -> None:
        for k, v in d.items():
            if isinstance(v, dict):
                if "ci_job" in v:
                    ci_job = v.get("ci_job")
                    mirror = v.get("mirror") or k
                    if isinstance(ci_job, str):
                        mapping[ci_job] = mirror
                else:
                    _walk(v, k)
            else:
                # support legacy flat mapping where value is string
                if isinstance(v, str) and prefix is None:
                    mapping[k] = v

    _walk(data)
    return mapping


def find_unmapped_ci_jobs(
    discovered: List[object] | None = None, mapping: Dict[str, str] | None = None
) -> Set[str]:
    """Return set of discovered job keys not present in mapping.

    If called with no arguments, this function will attempt to discover
    CI jobs from `.github/workflows` and load the local mirror mapping
    from `.firsttry/ci_mirror.toml`.

    A discovered job is keyed as `workflow/job_id` to match the mapping file.
    """

    missing: List[object] = []

    # Lazy import the discovery helper to avoid an import cycle at module load.
    if discovered is None:
        try:
            from firsttry.ci_discovery.reader import discover_ci_jobs

            discovered = discover_ci_jobs()
        except Exception:
            discovered = []

    if mapping is None:
        mapping = load_mirror_config()

    for job in discovered:
        job_id = getattr(job, "job_id", None)
        # mapping keys are job_id -> mirror name (backwards compatible parsing)
        if job_id not in mapping:
            missing.append(job)
    return missing


__all__ = ["load_mirror_config", "find_unmapped_ci_jobs"]
