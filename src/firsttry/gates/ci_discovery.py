from __future__ import annotations

import glob
import os
import pathlib
from typing import Any, Dict, List, Optional

from .config import CiMirrorConfig, Job, Plan, Step

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _require_yaml() -> None:
    if yaml is None:
        raise RuntimeError(
            "YAML support not available. Install 'pyyaml' to use CI discovery:\n"
            "  python -m pip install pyyaml"
        )


def _find_workflow_files(root: pathlib.Path) -> List[pathlib.Path]:
    pattern = str(root / ".github" / "workflows" / "*.yml")
    paths = [pathlib.Path(p) for p in glob.glob(pattern)]
    pattern2 = str(root / ".github" / "workflows" / "*.yaml")
    paths.extend(pathlib.Path(p) for p in glob.glob(pattern2))
    # Deduplicate and sort
    seen = set()
    uniq: List[pathlib.Path] = []
    for p in paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return sorted(uniq)


def _load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    _require_yaml()
    with path.open("r", encoding="utf8") as f:
        data = yaml.safe_load(f)  # type: ignore[call-arg]
    return data or {}


def _guess_tags_for_job(workflow_name: str, job_id: str) -> List[str]:
    name = f"{workflow_name}:{job_id}".lower()
    tags: List[str] = []

    # crude but effective heuristics
    if any(k in name for k in ("lint", "style", "ruff", "flake")):
        tags.append("dev_gate")
        tags.append("merge_gate")
    if any(k in name for k in ("test", "pytest", "ci")):
        tags.append("dev_gate")
        tags.append("merge_gate")
    if any(k in name for k in ("release", "publish", "deploy")):
        tags.append("merge_gate")
        tags.append("release_gate")
    if not tags:
        # default: dev + merge
        tags.extend(["dev_gate", "merge_gate"])
    # de-dup while preserving order
    seen = set()
    uniq: List[str] = []
    for t in tags:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq


def _normalize_workflow_name(path: pathlib.Path) -> str:
    # e.g. ".github/workflows/ci.yml" -> "ci.yml"
    return path.name


def discover_ci(
    root: pathlib.Path,
) -> CiMirrorConfig:
    """
    Discover CI jobs and steps from GitHub Actions workflows.

    Best effort:
      - Jobs become [jobs.*] entries
      - Each job gets a corresponding plan with the 'run:' steps
    """
    wf_files = _find_workflow_files(root)
    jobs: Dict[str, Job] = {}
    plans: Dict[str, Plan] = {}

    for wf_path in wf_files:
        wf_name = _normalize_workflow_name(wf_path)
        data = _load_yaml(wf_path)
        jobs_block = data.get("jobs") or {}
        if not isinstance(jobs_block, dict):
            continue

        for job_id, job_def in jobs_block.items():
            if not isinstance(job_def, dict):
                continue

            steps_def = job_def.get("steps") or []
            if not isinstance(steps_def, list):
                continue

            plan_name = f"{job_id}_plan"
            step_objs: List[Step] = []
            step_idx = 0
            for s in steps_def:
                if not isinstance(s, dict):
                    continue
                run_cmd = s.get("run")
                if not run_cmd:
                    continue
                step_idx += 1
                step_id = str(s.get("name") or f"step-{step_idx}")
                step_objs.append(Step(id=step_id, run=str(run_cmd)))

            if not step_objs:
                # job has no run steps; skip
                continue

            plans[plan_name] = Plan(name=plan_name, steps=step_objs)

            tags = _guess_tags_for_job(wf_name, job_id)
            job_key = f"{wf_name}:{job_id}"
            jobs[job_key] = Job(
                name=job_key,
                workflow=wf_name,
                job_name=job_id,
                tags=tags,
                plan=plan_name,
                cloud_only=False,
            )

    return CiMirrorConfig(jobs=jobs, plans=plans)


def _quote(s: str) -> str:
    return s.replace('"', '\\"')


def _dump_ci_mirror_toml(ci_cfg: CiMirrorConfig) -> str:
    lines: List[str] = []

    # jobs
    for job in sorted(ci_cfg.jobs.values(), key=lambda j: j.name):
        lines.append(f'[jobs."{_quote(job.name)}"]')
        if job.workflow:
            lines.append(f'workflow = "{_quote(job.workflow)}"')
        if job.job_name:
            lines.append(f'job_name = "{_quote(job.job_name)}"')
        if job.tags:
            tags_str = ", ".join(f'"{_quote(t)}"' for t in job.tags)
            lines.append(f"tags = [{tags_str}]")
        if job.plan:
            lines.append(f'plan = "{_quote(job.plan)}"')
        if job.cloud_only:
            lines.append("cloud_only = true")
        lines.append("")  # blank line

    # plans
    for plan in sorted(ci_cfg.plans.values(), key=lambda p: p.name):
        lines.append(f'[plans."{_quote(plan.name)}"]')
        for step in plan.steps:
            lines.append('[[plans."%s".steps]]' % _quote(plan.name))
            lines.append(f'id = "{_quote(step.id)}"')
            # Use TOML multi-line basic string when the run command contains newlines.
            if "\n" in step.run:
                # Escape any triple-quote occurrences to avoid closing the string early.
                safe = step.run.replace('"""', '\\"""')
                lines.append('run = """%s"""' % safe)
            else:
                lines.append(f'run = "{_quote(step.run)}"')
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_ci_mirror_file(
    root: pathlib.Path,
    path: pathlib.Path,
    ci_cfg: CiMirrorConfig,
    overwrite: bool = False,
) -> pathlib.Path:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing CI mirror config: {path}")
    text = _dump_ci_mirror_toml(ci_cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf8")
    return path


def discover_and_write_ci_mirror(
    root: Optional[pathlib.Path] = None,
    filename: str = ".firsttry/ci_mirror.toml",
    overwrite: bool = False,
) -> pathlib.Path:
    root = root or pathlib.Path(os.getcwd())
    ci_cfg = discover_ci(root)
    target = root / filename
    return write_ci_mirror_file(root, target, ci_cfg, overwrite=overwrite)
