from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

from . import util
from .detector import detect
from .detector import load_user_overrides
from .util import Step


@dataclass
class Plan:
    profile: str
    steps: List[Step]
    env: Dict[str, str]


def _apply_scope_to_cmd(cmd: Sequence[str], scope_files: Sequence[str]) -> List[str]:
    # For black/ruff/mypy add paths; for pytest choose smoke flags later.
    base = list(cmd)
    if not base:
        return []
    tool = base[0]
    if tool in ("black", "ruff", "mypy"):
        if scope_files:
            return base + list(scope_files)
        # fallback common paths
        paths: List[str] = []
        if util.has_dir("src"):
            paths.append("src")
        if util.has_dir("tests"):
            paths.append("tests")
        return base + paths if paths else base
    return base


def _pytest_smoke_cmd(discovered_cmd: Sequence[str]) -> List[str]:
    # Keep discovered flags but run small subset by default.
    base: List[str] = []
    dc = list(discovered_cmd)
    if not dc:
        return []
    # adopt python -m pytest style if present
    if dc[0] == "python":
        base = dc[:]
        # append smoke marker
        if "-k" not in base and "-m" not in base:
            base += ["-k", "not slow"]
        return base
    base = dc[:]
    if "-k" not in base and "-m" not in base:
        base += ["-k", "not slow"]
    return base


def build_plan(profile: str) -> Plan:
    det = detect()
    overrides = load_user_overrides()
    env = det.env.copy()
    steps: List[Step] = []

    # Resolve include list from overrides (per profile) or default
    include = None
    prof = overrides.get("profiles", {}).get(profile, {})
    inc = prof.get("include")
    if isinstance(inc, list):
        include = set(inc)

    files: List[str] = list(util.staged_or_changed_paths())
    threshold: Optional[int] = None
    # Pull a discovered threshold if any
    for d in det.steps:
        sid: Any = d.get("id")
        if sid == "coverage-threshold":
            th = d.get("threshold")
            if isinstance(th, int):
                threshold = th

    # Build Steps from detected specs, skipping non-command specs (like coverage-threshold)
    for d in det.steps:
        tid_any: Any = d.get("id")
        if not isinstance(tid_any, str):
            continue
        tid = tid_any
        if tid == "coverage-threshold":
            continue
        if include is not None and tid not in include:
            continue
        raw_cmd: Any = d.get("cmd")
        # Only accept list[str] commands; otherwise skip safely
        if not isinstance(raw_cmd, list) or any(not isinstance(x, str) for x in raw_cmd):
            continue
        cmd: List[str] = list(raw_cmd)

        if profile in ("pre-commit", "commit"):
            if tid in ("black", "ruff", "mypy"):
                cmd = _apply_scope_to_cmd(cmd, files)
            if tid == "pytest":
                cmd = _pytest_smoke_cmd(cmd)
        elif profile in ("pre-push", "push"):
            if tid in ("black", "ruff", "mypy"):
                cmd = _apply_scope_to_cmd(cmd, files or [])
            if tid == "pytest":
                # fast but broader
                if "-k" not in cmd and "-m" not in cmd:
                    cmd = cmd + ["-m", "not slow"]
        # CI: leave cmd as-is
        steps.append(Step(id=tid, cmd=cmd, env=env))

    if profile == "ci":
        # If pytest present and threshold known, append threshold flags (idempotent)
        has_pytest = any(s.id == "pytest" for s in steps)
        if has_pytest and threshold is not None:
            for step in steps:
                if step.id == "pytest":
                    if not any(
                        isinstance(a, str) and a.startswith("--cov-fail-under") for a in step.cmd
                    ):
                        step.cmd = list(step.cmd) + [f"--cov-fail-under={threshold}"]
                    break
        # packaging probe
        steps.append(Step(id="packaging", cmd=["python", "-m", "build"], env=env))
        # If bandit detected in workflows, ensure it is in CI plan
        if any(dspec.get("id") == "bandit" for dspec in det.steps) and not any(
            s.id == "bandit" for s in steps
        ):
            steps.append(Step(id="bandit", cmd=["bandit", "-q", "-r", "src"], env=env))
        # If codeql seen, place a placeholder execution step (project may have proper init)
        if any(dspec.get("id") == "codeql" for dspec in det.steps) and not any(
            s.id == "codeql" for s in steps
        ):
            steps.append(
                Step(id="codeql", cmd=["codeql", "database", "analyze"], env=env, allow_fail=True)
            )

    return Plan(profile=profile, steps=steps, env=env)
