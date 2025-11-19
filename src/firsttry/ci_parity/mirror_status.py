"""Mirror drift detection helpers.

Provides a minimal `get_mirror_status()` implementation that compares the
workflows present under `.github/workflows` with the entries recorded in
`.firsttry/ci_mirror.toml`. The current mirror format does not store file
hashes, so the status is considered STALE when the set of workflow filenames
doesn't match the mirror's recorded workflows or when the mirror file is
missing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from .intents import (
    DEFAULT_MIRROR_PATH,
    DEFAULT_WORKFLOWS_ROOT,
    _iter_workflow_files,
    _load_mirror_jobs,
)


@dataclass(frozen=True)
class MirrorStatus:
    is_fresh: bool
    missing_workflows: List[str]
    extra_workflows: List[str]
    # For future use: per-workflow fingerprints
    fingerprints: Optional[dict] = None


def _fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    data = path.read_bytes()
    h.update(data)
    return h.hexdigest()


def get_mirror_status(
    mirror_path: Optional[str | Path] = None,
    workflows_root: Optional[str | Path] = None,
) -> MirrorStatus:
    mpath = Path(mirror_path) if mirror_path is not None else DEFAULT_MIRROR_PATH
    wroot = (
        Path(workflows_root) if workflows_root is not None else DEFAULT_WORKFLOWS_ROOT
    )

    # Discover workflows on disk
    workflow_files = [p.name for p in _iter_workflow_files(wroot)]
    workflow_set: Set[str] = set(workflow_files)

    # Load mirror entries (best-effort)
    try:
        mirror_jobs = _load_mirror_jobs(mpath)
    except Exception:
        # Mirror missing or unreadable -> stale
        return MirrorStatus(
            is_fresh=False,
            missing_workflows=sorted(list(workflow_set)),
            extra_workflows=[],
            fingerprints=None,
        )

    mirror_workflows = {mj.workflow for mj in mirror_jobs}

    missing = sorted([w for w in workflow_set if w not in mirror_workflows])
    extra = sorted([w for w in mirror_workflows if w not in workflow_set])

    is_fresh = not missing and not extra

    # Optionally compute fingerprints for present workflows (lightweight)
    fingerprints = {}
    for wf in workflow_files:
        p = wroot / wf
        try:
            fingerprints[wf] = _fingerprint(p)
        except Exception:
            fingerprints[wf] = ""

    return MirrorStatus(
        is_fresh=is_fresh,
        missing_workflows=missing,
        extra_workflows=extra,
        fingerprints=fingerprints,
    )
