"""CI-intent helpers: workflow scanning, mirror parsing, and autofill.

This module implements the behavior used by the `ci-intent-lint` and
`ci-intent-autofill` CLI commands and by the CI parity runner.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_MIRROR_PATH = Path(".firsttry") / "ci_mirror.toml"
DEFAULT_WORKFLOWS_ROOT = Path(".github") / "workflows"


@dataclasses.dataclass(frozen=True)
class CiJob:
    workflow: str
    job_id: str
    job_name: str | None = None

    @property
    def key(self) -> Tuple[str, str]:
        return (self.workflow, self.job_id)


@dataclasses.dataclass(frozen=True)
class MirrorJob:
    workflow: str
    job_id: str
    plan: str | None = None
    stage: str | None = None

    @property
    def key(self) -> Tuple[str, str]:
        return (self.workflow, self.job_id)


def _iter_workflow_files(root: Path = DEFAULT_WORKFLOWS_ROOT) -> Iterable[Path]:
    if not root.exists():
        return []
    for ext in ("*.yml", "*.yaml"):
        yield from root.glob(ext)


def _load_ci_jobs(workflows_root: Path = DEFAULT_WORKFLOWS_ROOT) -> List[CiJob]:
    jobs: List[CiJob] = []
    for wf_path in _iter_workflow_files(workflows_root):
        try:
            data = yaml.safe_load(wf_path.read_text()) or {}
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"[ci-parity] ERROR: Failed to parse workflow {wf_path}: {exc}",
                file=sys.stderr,
            )
            raise

        wf_name = wf_path.name
        wf_jobs = (data or {}).get("jobs") or {}
        if not isinstance(wf_jobs, dict):
            continue

        for job_id, job_def in wf_jobs.items():
            job_name = None
            if isinstance(job_def, dict):
                jn = job_def.get("name")
                if isinstance(jn, str):
                    job_name = jn
            jobs.append(CiJob(workflow=wf_name, job_id=job_id, job_name=job_name))
    return jobs


def _load_mirror_jobs(mirror_path: Path) -> List[MirrorJob]:
    if not mirror_path.exists():
        raise FileNotFoundError(mirror_path)

    raw = tomllib.loads(mirror_path.read_text())
    raw_jobs = raw.get("jobs") or []
    if not isinstance(raw_jobs, list):
        raise ValueError("Expected [[jobs]] array in ci_mirror.toml")

    jobs: List[MirrorJob] = []
    for idx, item in enumerate(raw_jobs):
        if not isinstance(item, dict):
            print(
                f"[ci-parity] WARNING: jobs[{idx}] is not a table; skipping",
                file=sys.stderr,
            )
            continue
        wf = item.get("workflow")
        jid = item.get("job_id")
        if not isinstance(wf, str) or not isinstance(jid, str):
            print(
                f"[ci-parity] WARNING: jobs[{idx}] missing workflow/job_id; skipping",
                file=sys.stderr,
            )
            continue
        plan = item.get("plan") if isinstance(item.get("plan"), str) else None
        stage = item.get("stage") if isinstance(item.get("stage"), str) else None
        jobs.append(MirrorJob(workflow=wf, job_id=jid, plan=plan, stage=stage))
    return jobs


def _compute_unmapped(
    ci_jobs: List[CiJob], mirror_jobs: List[MirrorJob]
) -> Tuple[List[CiJob], List[MirrorJob]]:
    ci_index: Dict[Tuple[str, str], CiJob] = {j.key: j for j in ci_jobs}
    mirror_index: Dict[Tuple[str, str], MirrorJob] = {j.key: j for j in mirror_jobs}

    unmapped_ci: List[CiJob] = [
        j for key, j in ci_index.items() if key not in mirror_index
    ]
    stale_mirror: List[MirrorJob] = [
        j for key, j in mirror_index.items() if key not in ci_index
    ]
    return unmapped_ci, stale_mirror


def lint_intents(
    mirror_path: str | Path | None = None,
    workflows_root: str | Path | None = None,
) -> int:
    """
    Lint CI intents by comparing GitHub workflows to ci_mirror.toml.

    Returns:
      0 if everything is mapped,
      2 if there are unmapped CI jobs or stale mirror entries,
      1 on fatal error.
    """
    mpath = Path(mirror_path) if mirror_path is not None else DEFAULT_MIRROR_PATH
    wroot = (
        Path(workflows_root) if workflows_root is not None else DEFAULT_WORKFLOWS_ROOT
    )

    try:
        ci_jobs = _load_ci_jobs(wroot)
    except Exception:
        return 1

    if not ci_jobs:
        print(
            "[ci-parity] WARNING: No CI jobs discovered under .github/workflows",
            file=sys.stderr,
        )

    try:
        mirror_jobs = _load_mirror_jobs(mpath)
    except FileNotFoundError:
        print(f"[ci-parity] ERROR: Mirror file not found: {mpath}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"[ci-parity] ERROR: Failed to load mirror file {mpath}: {exc}",
            file=sys.stderr,
        )
        return 1

    unmapped_ci, stale_mirror = _compute_unmapped(ci_jobs, mirror_jobs)

    if not unmapped_ci and not stale_mirror:
        print("[ci-parity] OK: All CI jobs are mapped in ci_mirror.toml")
        return 0

    if unmapped_ci:
        print(
            "[ci-parity] Unmapped CI jobs (present in workflows but missing in mirror):"
        )
        for j in sorted(unmapped_ci, key=lambda x: (x.workflow, x.job_id)):
            suffix = f" ({j.job_name})" if j.job_name else ""
            print(f"  - {j.workflow}:{j.job_id}{suffix}")

    if stale_mirror:
        print(
            "[ci-parity] Stale mirror entries (present in mirror but missing in workflows):"
        )
        for j in sorted(stale_mirror, key=lambda x: (x.workflow, x.job_id)):
            print(f"  - {j.workflow}:{j.job_id} (plan={j.plan!r}, stage={j.stage!r})")

    # Treat unmapped / stale as a parity failure (not a crash)
    return 2


def autofill_intents(
    mirror_path: str | Path | None = None,
    workflows_root: str | Path | None = None,
    dry_run: bool = True,
) -> int:
    """
    Suggest or apply intent mappings for unmapped CI jobs.

    When dry_run=True, prints suggested [[jobs]] entries but does not modify the file.
    When dry_run=False, appends those entries to the mirror (creating it if needed).
    """
    mpath = Path(mirror_path) if mirror_path is not None else DEFAULT_MIRROR_PATH
    wroot = (
        Path(workflows_root) if workflows_root is not None else DEFAULT_WORKFLOWS_ROOT
    )

    try:
        ci_jobs = _load_ci_jobs(wroot)
    except Exception:
        return 1

    existing_mirror_jobs: List[MirrorJob]
    if mpath.exists():
        try:
            existing_mirror_jobs = _load_mirror_jobs(mpath)
        except Exception as exc:
            print(
                f"[ci-parity] ERROR: Failed to load mirror file {mpath}: {exc}",
                file=sys.stderr,
            )
            return 1
    else:
        existing_mirror_jobs = []
        print(
            f"[ci-parity] NOTE: Mirror file {mpath} does not exist; starting from empty",
            file=sys.stderr,
        )

    unmapped_ci, _ = _compute_unmapped(ci_jobs, existing_mirror_jobs)
    if not unmapped_ci:
        print("[ci-parity] OK: No unmapped CI jobs; nothing to autofill.")
        return 0

    print("[ci-parity] Suggested mirror entries for unmapped CI jobs:")
    suggested_entries: List[str] = []
    for j in sorted(unmapped_ci, key=lambda x: (x.workflow, x.job_id)):
        plan = f"gha_{j.workflow.replace('.yml', '').replace('.yaml', '').replace('-', '_')}__{j.job_id}"
        line = (
            "[[jobs]]\n"
            f'workflow = "{j.workflow}"\n'
            f'job_id = "{j.job_id}"\n'
            f'plan = "{plan}"\n'
        )
        suggested_entries.append(line)
        suffix = f" ({j.job_name})" if j.job_name else ""
        print(f"  - {j.workflow}:{j.job_id}{suffix} → plan={plan}")

    if dry_run:
        print("\n[ci-parity] Dry-run mode; mirror will NOT be modified.")
        print(
            f"[ci-parity] To apply these suggestions, re-run without --dry-run and add them to {mpath}."
        )
        return 0

    if not mpath.parent.exists():
        mpath.parent.mkdir(parents=True, exist_ok=True)
    with mpath.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(suggested_entries))
        fh.write("\n")

    print(f"[ci-parity] Appended {len(suggested_entries)} entries to {mpath}")
    return 0
    return 0
