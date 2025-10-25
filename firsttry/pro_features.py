"""
pro_features.py
----------------

Executes the repo's adapted CI plan locally (fast) and stops at
the first failing step. This simulates what GitHub Actions would
do to your pull request, *before you push*.

This is the core of FirstTry Pro:
- License-gated
- Early stop for speed
- Forensic `failed_at` block with a fix hint
"""

import subprocess
import time
from typing import Any, Dict, List, Optional
from types import ModuleType

# optional quickfix integration (best-effort; keep pro_features import-safe)
# Import into a typed variable so mypy is happy when quickfix is absent.
quickfix: ModuleType | None = None
try:
    # Import the package-level quickfix module if available.
    from firsttry import quickfix as _q

    quickfix = _q
except Exception:  # pragma: no cover - defensive
    quickfix = None


def normalize_license(payload: Any) -> Dict[str, Any]:
    """Lightweight compatibility helper used by some tests.

    Accepts either a dict with 'plan' and 'features' or a legacy list of features.
    Returns a normalized dict {"plan": str, "features": List[str]}.
    """
    if payload is None:
        return {"plan": "free", "features": []}
    if isinstance(payload, dict):
        plan = payload.get("plan", "free")
        features = payload.get("features", [])
        if not isinstance(features, list):
            features = [str(features)]
        return {"plan": str(plan), "features": [str(f) for f in features]}
    if isinstance(payload, list):
        return {"plan": "free", "features": [str(x) for x in payload]}
    return {"plan": "free", "features": []}


def run_ci_steps_locally(
    plan: Dict[str, Any] | List[str], license_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Backwards-compatible runner used by older CLI/tests. Executes all steps
    (does not stop early), enforces a license for dict plans, and returns
    shape: {"ok": bool, "results": [ {job, step, returncode, output, cmd}, ... ]}
    """
    # Detect legacy invocation where a list of shell commands was provided.
    legacy_mode = isinstance(plan, list)

    # Normalize legacy list-of-commands input into plan dict
    if legacy_mode:
        steps = []
        for i, cmd in enumerate(plan):
            steps.append({"name": f"step-{i}", "run": cmd})
        plan = {"jobs": [{"job_name": "legacy", "steps": steps}]}

    # License gating: require license when plan is a dict (non-legacy)
    if license_key is not None:
        try:
            _assert_license_is_valid(license_key)
        except ProFeatureError as exc:
            return {
                "ok": False,
                "results": [
                    {
                        "job": "license-check",
                        "step": "validate-license",
                        "returncode": 1,
                        "output": f"License validation failed: {exc}",
                    }
                ],
            }
    else:
        # If no license provided and not legacy, block
        if not legacy_mode:
            return {
                "ok": False,
                "results": [
                    {
                        "job": "license-check",
                        "step": "validate-license",
                        "returncode": 1,
                        "output": "License validation failed: No license key provided",
                    }
                ],
            }

    results: List[Dict[str, Any]] = []
    overall_ok = True

    plan_dict = plan if isinstance(plan, dict) else {"jobs": []}

    DANGEROUS_TOKENS = [
        "rm -rf /",
        "rm -rf ~",
        "shutdown",
        "reboot",
        ":(){ :|:& };:",  # fork bomb
    ]

    def _is_command_safe(cmd_str: str) -> bool:
        lowered = cmd_str.lower()
        for bad in DANGEROUS_TOKENS:
            if bad in lowered:
                return False
        return True

    for job in plan_dict.get("jobs", []):
        job_name = job.get("job_name") or job.get("job_id") or "unknown-job"
        for step in job.get("steps", []):
            step_name = step.get("name") or step.get("step_name") or "unnamed-step"
            cmd = step.get("run") or step.get("cmd") or ""
            if not cmd:
                results.append(
                    {
                        "job": job_name,
                        "step": step_name,
                        "returncode": None,
                        "output": "SKIPPED (no 'run' provided)",
                    }
                )
                continue

            if not _is_command_safe(str(cmd)):
                results.append(
                    {
                        "job": job_name,
                        "step": step_name,
                        "cmd": cmd,
                        "status": "blocked",
                        "reason": "blocked_for_safety",
                        "stdout": "",
                        "stderr": "Command blocked by safety policy",
                        "returncode": None,
                    }
                )
                overall_ok = False
                continue

            completed = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            rc = completed.returncode
            out = f"STDOUT:\n{completed.stdout.strip()}\n\nSTDERR:\n{completed.stderr.strip()}"

            results.append(
                {
                    "job": job_name,
                    "step": step_name,
                    "cmd": cmd,
                    "returncode": rc,
                    "output": out,
                }
            )
            if rc != 0:
                overall_ok = False

    return {"ok": overall_ok, "results": results}


class ProFeatureError(RuntimeError):
    pass


def _assert_license_is_valid(license_key: Optional[str]) -> None:
    """
    Minimal validation. Production would call remote license API.
    TEST-KEY-OK is accepted in tests.
    """
    if not license_key:
        raise ProFeatureError("No license key provided")
    if license_key == "TEST-KEY-OK":
        return
    # In real mode you'd verify remotely.
    return


def _run_single_command(cmd: str) -> Dict[str, Any]:
    """
    Run a shell command fast, capture output and timing.
    """
    start = time.time()
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    end = time.time()

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "duration_sec": round(end - start, 3),
    }


def run_ci_plan_locally(
    plan: Dict[str, Any], license_key: Optional[str]
) -> Dict[str, Any]:
    """
    Execute plan from ci_mapper.build_ci_plan().

    Returns structured result:
    {
      "ok": True/False,
      "summary": {
        "total_jobs": N,
        "total_steps": M,
        "failed_at": { ... } or None,
        "runtime_sec": 1.234
      },
      "jobs": [
        {
          "job_name": "...",
          "workflow_name": "...",
          "steps": [
            {
              "step_name": "---",
              "cmd": "...",
              "install": False,
              "duration_sec": 0.12,
              "returncode": 0,
              "stdout": "...",
              "stderr": "..."
            },
            ...
          ]
        },
        ...
      ]
    }

    Behavior:
    - stops on first failing step for speed.
    - failure record includes WHERE and WHAT, so we can report precisely.
    """

    # license check first
    try:
        _assert_license_is_valid(license_key)
    except ProFeatureError as exc:
        return {
            "ok": False,
            "summary": {
                "total_jobs": 0,
                "total_steps": 0,
                "failed_at": {
                    "reason": "license",
                    "message": str(exc),
                },
                "runtime_sec": 0.0,
            },
            "jobs": [],
        }

    t0 = time.time()
    jobs_report: List[Dict[str, Any]] = []
    total_steps = 0
    failed_at = None
    overall_ok = True

    for job in plan.get("jobs", []):
        job_name = job["job_name"]
        wf_name = job.get("workflow_name", "unknown-workflow")
        job_steps_report: List[Dict[str, Any]] = []

        for step in job["steps"]:
            total_steps += 1
            cmd = step["cmd"]
            step_name = step["step_name"]

            result = _run_single_command(cmd)

            step_entry = {
                "step_name": step_name,
                "cmd": cmd,
                "install": step["install"],
                "duration_sec": result["duration_sec"],
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "job": job_name,
                "workflow_name": wf_name,
                "meta": step["meta"],
            }
            job_steps_report.append(step_entry)

            if result["returncode"] != 0 and failed_at is None:
                # record the first failure with full forensic detail
                # Provide a best-effort quick-fix hint using the optional quickfix module.
                # Default to a short, actionable suggestion (more helpful than a generic sentence).
                hint_text = "Run the failing command locally to reproduce and fix it."
                try:
                    # First prefer the quickfix reference imported into this module (if any)
                    if quickfix is not None and hasattr(quickfix, "suggest_fix"):
                        specific = quickfix.suggest_fix(
                            cmd=cmd,
                            stdout=result.get("stdout", ""),
                            stderr=result.get("stderr", ""),
                        )
                        if specific:
                            hint_text = specific
                    else:
                        # Fall back to importing the package quickfix module at runtime
                        try:
                            from firsttry import quickfix as _pkg_q

                            if _pkg_q is not None and hasattr(_pkg_q, "suggest_fix"):
                                specific = _pkg_q.suggest_fix(
                                    cmd=cmd,
                                    stdout=result.get("stdout", ""),
                                    stderr=result.get("stderr", ""),
                                )
                                if specific:
                                    hint_text = specific
                        except Exception:
                            # ignore package-level quickfix failures
                            pass
                except Exception:
                    # Don't let quickfix errors break the runner; fall back to generic hint.
                    hint_text = (
                        "This is the first failing step. Fix this step to unblock CI."
                    )

                failed_at = {
                    "workflow_name": wf_name,
                    "job_name": job_name,
                    "step_name": step_name,
                    "cmd": cmd,
                    "returncode": result["returncode"],
                    "stderr": result["stderr"],
                    "stdout": result["stdout"],
                    "duration_sec": result["duration_sec"],
                    "hint": hint_text,
                }
                overall_ok = False
                # STOP EARLY for speed
                break

        jobs_report.append(
            {
                "job_name": job_name,
                "workflow_name": wf_name,
                "steps": job_steps_report,
            }
        )

        # stop entire run on first failure to keep it fast
        if not overall_ok:
            break

    t1 = time.time()

    return {
        "ok": overall_ok,
        "summary": {
            "total_jobs": len(plan.get("jobs", [])),
            "total_steps": total_steps,
            "failed_at": failed_at,
            "runtime_sec": round(t1 - t0, 3),
        },
        "jobs": jobs_report,
    }
