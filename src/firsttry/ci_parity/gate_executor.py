from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple
import time

from firsttry.ci_parity.step_runner import (
    StepResult as ParityStepResult,
    run_step_with_fallback,
    print_gate_plan_summary,
)


def execute_plan_steps(
    plan_name: str,
    steps: Iterable[Any],
    *,
    cwd: Path,
    env: Mapping[str, str] | None,
) -> Tuple[int, List[ParityStepResult]]:
    """
    Execute all steps in a plan using run_step_with_fallback.

    Steps may be objects with attributes `id`, `run`, and optionally `intent`.
    Returns (exit_code, step_results).
    """
    results: List[ParityStepResult] = []

    for step in steps:
        step_dict: Dict[str, Any] = {"id": getattr(step, "id", None), "run": getattr(step, "run", "")}
        intent = getattr(step, "intent", None)
        if intent:
            step_dict["intent"] = intent

        # Determine per-step timeout: prefer explicit env mapping value
        timeout_s = None
        try:
            if env and "FIRSTTRY_STEP_TIMEOUT" in env:
                timeout_s = int(env.get("FIRSTTRY_STEP_TIMEOUT") or 0) or None
        except Exception:
            timeout_s = None

        start = time.time()
        res = run_step_with_fallback(step_dict, cwd=cwd, env=env, timeout_s=timeout_s)
        dur = time.time() - start

        # The Parity StepResult does not include duration; we can attach it
        # dynamically if callers expect it (they won't rely on it in parity).
        # attach duration as attribute for downstream printing if desired
        try:
            setattr(res, "duration_s", dur)
        except Exception:
            pass
        results.append(res)

        if res.returncode != 0:
            break

    # Print per-plan summary for the user
    print_gate_plan_summary(plan_name, results)

    exit_code = 0
    for r in results:
        if r.returncode != 0:
            exit_code = r.returncode
            break

    return exit_code, results
