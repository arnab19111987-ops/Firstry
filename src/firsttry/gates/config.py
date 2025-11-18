from __future__ import annotations

import dataclasses
import os
import pathlib
from typing import Dict, List, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    import tomli as tomllib  # type: ignore


@dataclasses.dataclass
class Step:
    id: str
    run: str
    intent: Optional[str] = None


@dataclasses.dataclass
class Plan:
    name: str
    steps: List[Step]


@dataclasses.dataclass
class Job:
    name: str
    workflow: Optional[str]
    job_name: Optional[str]
    tags: List[str]
    plan: Optional[str]
    cloud_only: bool = False


@dataclasses.dataclass
class Gate:
    name: str
    tags: List[str]
    require_cloud_only_success_in_ci: bool = False


@dataclasses.dataclass
class CiMirrorConfig:
    jobs: Dict[str, Job]
    plans: Dict[str, Plan]


@dataclasses.dataclass
class PolicyConfig:
    gates: Dict[str, Gate]


def _load_toml(path: pathlib.Path) -> dict:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        # Fallback: be tolerant of TOML variants produced by our CI discovery
        # writer by using the third-party `toml` package which is more
        # permissive with certain multiline string formats.
        try:
            import toml

            return toml.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # As a last resort, return an empty mapping so callers can
            # handle the missing/invalid config gracefully.
            return {}


def load_ci_mirror(
    root: pathlib.Path | None = None,
    filename: str = ".firsttry/ci_mirror.toml",
) -> CiMirrorConfig:
    root = root or pathlib.Path(os.getcwd())
    path = root / filename
    if not path.is_file():
        raise FileNotFoundError(f"CI mirror config not found: {path}")

    data = _load_toml(path)

    # If TOML parsing failed or produced no data, fall back to on-the-fly
    # discovery from GitHub workflows. This ensures gates still run in
    # environments where the written `.firsttry/ci_mirror.toml` contains
    # permissive multiline content that strict tomllib cannot parse.
    if not data:
        try:
            from .ci_discovery import discover_ci

            return discover_ci(root)
        except Exception:
            # If discovery also fails, proceed with whatever (possibly
            # empty) data we have so callers can handle missing jobs.
            pass

    jobs_raw = data.get("jobs", {}) or {}
    plans_raw = data.get("plans", {}) or {}

    jobs: Dict[str, Job] = {}
    for job_name, j in jobs_raw.items():
        tags = list(j.get("tags", []) or [])
        plan = j.get("plan")
        cloud_only = bool(j.get("cloud_only", False))
        jobs[job_name] = Job(
            name=job_name,
            workflow=j.get("workflow"),
            job_name=j.get("job_name"),
            tags=tags,
            plan=plan,
            cloud_only=cloud_only,
        )

    plans: Dict[str, Plan] = {}
    for plan_name, p in plans_raw.items():
        steps_list = p.get("steps", []) or []
        steps: List[Step] = []
        for s in steps_list:
            steps.append(
                Step(id=str(s.get("id")), run=str(s.get("run")), intent=s.get("intent"))
            )
        plans[plan_name] = Plan(name=plan_name, steps=steps)

    return CiMirrorConfig(jobs=jobs, plans=plans)


def load_policy(
    root: pathlib.Path | None = None,
    filename: str = ".firsttry/policy.toml",
) -> PolicyConfig:
    root = root or pathlib.Path(os.getcwd())
    path = root / filename
    if not path.is_file():
        raise FileNotFoundError(f"Policy config not found: {path}")

    data = _load_toml(path)
    gates_raw = data.get("gates", {}) or {}

    gates: Dict[str, Gate] = {}
    for gate_name, g in gates_raw.items():
        tags = list(g.get("tags", []) or [])
        require_cloud = bool(
            g.get("require_cloud_only_in_ci", False)
            or g.get("require_cloud_only_success_in_ci", False)
        )
        gates[gate_name] = Gate(
            name=gate_name,
            tags=tags,
            require_cloud_only_success_in_ci=require_cloud,
        )

    return PolicyConfig(gates=gates)


def resolve_jobs_for_gate(
    ci_cfg: CiMirrorConfig,
    policy: PolicyConfig,
    gate_name: str,
) -> Tuple[List[Job], List[Job], List[Job]]:
    """
    Return (local_jobs, cloud_only_jobs, unmatched_jobs) for a given gate.

    - local_jobs: jobs whose tags intersect the gate's tags and are runnable locally
    - cloud_only_jobs: jobs whose tags intersect the gate's tags but are marked cloud_only
    - unmatched_jobs: jobs whose tags do NOT intersect the gate's tags at all
    """
    gate = policy.gates.get(gate_name)
    if not gate:
        raise KeyError(f"Gate '{gate_name}' not found in policy config")

    tag_set = set(gate.tags)
    local_jobs: List[Job] = []
    cloud_only_jobs: List[Job] = []
    unmatched_jobs: List[Job] = []

    for job in ci_cfg.jobs.values():
        job_tags = set(job.tags)
        if not tag_set.intersection(job_tags):
            # This job does not participate in this gate
            unmatched_jobs.append(job)
            continue

        if job.cloud_only:
            cloud_only_jobs.append(job)
        else:
            local_jobs.append(job)

    # Deterministic ordering for nicer output.
    local_jobs.sort(key=lambda j: j.name)
    cloud_only_jobs.sort(key=lambda j: j.name)
    unmatched_jobs.sort(key=lambda j: j.name)
    return local_jobs, cloud_only_jobs, unmatched_jobs
