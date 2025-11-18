from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess
import sys
import time
from typing import Dict, List, Literal, Optional, Tuple

from .bootstrap import ensure_ci_mirror_exists, ensure_policy_exists
from .ci_status import get_cloud_job_statuses
from .config import (
    CiMirrorConfig,
    Job,
    load_ci_mirror,
    load_policy,
    resolve_jobs_for_gate,
)
from .deps import suggest_dependency_fix

GateName = Literal["dev", "merge", "release"]


@dataclasses.dataclass
class StepResult:
    plan: str
    step_id: str
    cmd: str
    returncode: int
    duration_s: float


@dataclasses.dataclass
class JobResult:
    job: Job
    status: Literal["pass", "fail", "skipped"]
    reason: Optional[str] = None
    steps: List[StepResult] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class GateRun:
    gate: GateName
    local_results: List[JobResult]
    cloud_only_jobs: List[Job]
    unmatched_jobs: List[Job]
    started_at: float
    ended_at: float
    require_cloud_only_success_in_ci: bool = False
    cloud_only_failed_jobs: List[Job] = dataclasses.field(default_factory=list)
    cloud_statuses: Dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        return self.ended_at - self.started_at

    @property
    def ok(self) -> bool:
        # Skipped jobs are neutral; only explicit failures (or cloud-only CI failures)
        # should fail the gate.
        if any(j.status == "fail" for j in self.local_results):
            return False
        if self.require_cloud_only_success_in_ci and self.cloud_only_failed_jobs:
            return False
        return True


def _run_shell(
    cmd: str,
    *,
    cwd: pathlib.Path,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str, float]:
    env_full = os.environ.copy()
    if env:
        env_full.update(env)

    start = time.time()
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        env=env_full,
        text=True,
        capture_output=True,
    )
    end = time.time()
    return proc.returncode, proc.stdout, proc.stderr, end - start


def _run_plan_for_job(
    root: pathlib.Path,
    job: Job,
    ci_cfg: CiMirrorConfig,
) -> JobResult:
    if not job.plan:
        return JobResult(
            job=job,
            status="skipped",
            reason="no_plan_defined",
            steps=[],
        )

    plan = ci_cfg.plans.get(job.plan)
    if not plan:
        return JobResult(
            job=job,
            status="skipped",
            reason=f"plan_missing:{job.plan}",
            steps=[],
        )

    results: List[StepResult] = []
    status: Literal["pass", "fail"] = "pass"

    from firsttry.ci_parity.gate_executor import execute_plan_steps

    # Use the parity executor which prefers FirstTry-native wrappers and
    # falls back to raw CI commands on failure.
    exit_code, parity_results = execute_plan_steps(
        plan_name=plan.name, steps=plan.steps, cwd=root, env=os.environ.copy()
    )

    # parity_results are firsttry.ci_parity.step_runner.StepResult objects
    for pr in parity_results:
        results.append(
            StepResult(
                plan=plan.name,
                step_id=pr.step_id,
                cmd=pr.used_cmd,
                returncode=pr.returncode,
                duration_s=0.0,
            )
        )

    if exit_code != 0:
        status = "fail"
        # Try to emit dependency advice on first failure.
        # We don't have stderr capture here; suggest_dependency_fix may be
        # able to infer from the used command.
        suggest_dependency_fix(root=root, stderr="", cmd=plan.steps[0].run if plan.steps else "")

    return JobResult(job=job, status=status, steps=results)


def run_gate(
    gate_name: GateName,
    *,
    root: Optional[pathlib.Path] = None,
) -> GateRun:
    root = root or pathlib.Path(os.getcwd())
    # Bootstrap configs if missing.
    ensure_policy_exists(root=root)
    ensure_ci_mirror_exists(root=root)

    ci_cfg = load_ci_mirror(root=root)
    policy = load_policy(root=root)

    # Get gate config for this gate name
    gate_cfg = policy.gates.get(gate_name)
    if gate_cfg is None:
        raise KeyError(f"Gate '{gate_name}' not found in policy config")

    local_jobs, cloud_only_jobs, unmatched_jobs = resolve_jobs_for_gate(
        ci_cfg=ci_cfg,
        policy=policy,
        gate_name=gate_name,
    )

    # Cloud-only status lookup (optional)
    cloud_statuses = get_cloud_job_statuses(cloud_only_jobs, root=root)
    cloud_only_failed_jobs: List[Job] = [
        j for j in cloud_only_jobs if cloud_statuses.get(j.name) == "fail"
    ]

    start = time.time()
    local_results: List[JobResult] = []

    for job in local_jobs:
        jr = _run_plan_for_job(root=root, job=job, ci_cfg=ci_cfg)
        local_results.append(jr)

    end = time.time()
    return GateRun(
        gate=gate_name,
        local_results=local_results,
        cloud_only_jobs=cloud_only_jobs,
        unmatched_jobs=unmatched_jobs,
        started_at=start,
        ended_at=end,
        require_cloud_only_success_in_ci=gate_cfg.require_cloud_only_success_in_ci,
        cloud_only_failed_jobs=cloud_only_failed_jobs,
        cloud_statuses=cloud_statuses,
    )


def print_gate_summary(gr: GateRun) -> None:
    print(f"[FirstTry] {gr.gate.capitalize()} Gate Summary")
    print("-" * 60)
    print(f"Total duration: {gr.duration_s:.2f}s")
    print()

    # --------------------------
    # Checks that actually ran
    # --------------------------
    print("Checks RUN:")
    if not gr.local_results:
        print("  (none)")
    else:
        for jr in gr.local_results:
            status_icon = "✓" if jr.status == "pass" else ("…" if jr.status == "skipped" else "✗")
            wf = jr.job.workflow or "?"
            jn = jr.job.job_name or jr.job.name
            print(f"  {status_icon} {jr.job.name} (workflow: {wf}, job: {jn})")
            if not jr.steps:
                print("      - (no steps)")
            else:
                for st in jr.steps:
                    mark = ""
                    if st.returncode != 0:
                        mark = " [FAILED]"
                    print(f"      - {st.cmd}  [{st.duration_s:.2f}s]{mark}")

            if jr.status != "pass" and jr.reason:
                print(f"      reason: {jr.reason}")

    # --------------------------
    # Checks that were skipped
    # --------------------------
    print()
    print("Checks SKIPPED:")
    skipped_any = False

    # 1) cloud-only jobs
    for job in gr.cloud_only_jobs:
        skipped_any = True
        wf = job.workflow or "?"
        jn = job.job_name or job.name
        status = gr.cloud_statuses.get(job.name, "unknown")
        status_note = ""
        if status == "fail":
            status_note = " (CI status: FAIL)"
        elif status == "pass":
            status_note = " (CI status: PASS)"
        elif status == "unknown":
            status_note = " (CI status: unknown)"

        print(f"  - {job.name} (workflow: {wf}, job: {jn}){status_note}")
        print("      reason: cloud-only job (not runnable locally)")

    # 2) local jobs that were explicitly skipped (missing plan, etc.)
    for jr in gr.local_results:
        if jr.status == "skipped":
            skipped_any = True
            wf = jr.job.workflow or "?"
            jn = jr.job.job_name or jr.job.name
            print(f"  - {jr.job.name} (workflow: {wf}, job: {jn})")
            print(f"      reason: {jr.reason or 'skipped'}")

    # 3) jobs that didn't match this gate's tags at all
    for job in gr.unmatched_jobs:
        skipped_any = True
        wf = job.workflow or "?"
        jn = job.job_name or job.name
        print(f"  - {job.name} (workflow: {wf}, job: {jn})")
        print(
            f"      reason: job tags {job.tags!r} do not intersect gate tags "
            f"(this gate tags = {gr.gate})"
        )

    if not skipped_any:
        print("  (none)")

    # --------------------------
    # Failed checks summary
    # --------------------------
    print()
    print("Failed checks:")
    failed_local = [jr for jr in gr.local_results if jr.status == "fail"]
    failed_cloud = gr.cloud_only_failed_jobs if gr.require_cloud_only_success_in_ci else []

    if not failed_local and not failed_cloud:
        print("  (none)")
    else:
        for jr in failed_local:
            wf = jr.job.workflow or "?"
            jn = jr.job.job_name or jr.job.name
            print(f"  - {jr.job.name} (workflow: {wf}, job: {jn})")
            if jr.steps:
                # first non-zero step, or last step
                failing_step = next(
                    (st for st in jr.steps if st.returncode != 0),
                    jr.steps[-1],
                )
                print(
                    f"      last failing step: '{failing_step.step_id}' "
                    f"returned {failing_step.returncode}"
                )
                print(f"      cmd: {failing_step.cmd!r}")

        for job in failed_cloud:
            wf = job.workflow or "?"
            jn = job.job_name or job.name
            print(f"  - {job.name} (workflow: {wf}, job: {jn})")
            print("      failure: cloud-only CI job marked FAIL in .firsttry/ci_status.json")

    print()
    if gr.ok:
        print(f"Result: ✅ {gr.gate.capitalize()} gate PASSED")
    else:
        if gr.cloud_only_failed_jobs and gr.require_cloud_only_success_in_ci:
            print("Note: One or more cloud-only CI jobs are failing and this gate is configured")
            print("      with 'require_cloud_only_success_in_ci = true'.")
        print(f"Result: ❌ {gr.gate.capitalize()} gate FAILED")
