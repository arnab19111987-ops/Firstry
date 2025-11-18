from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from typing import List

from .intent_resolver import ResolvedCommand, resolve_command_for_step


@dataclass
class StepResult:
    step_id: str
    intent_key: Optional[str]
    used_cmd: str
    raw_cmd: str
    used_source: str
    fallback_used: bool
    returncode: int
    timed_out: bool = False
    timeout_s: Optional[int] = None


def _run_shell(
    cmd: str,
    *,
    cwd: Path,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        text=True,
        timeout=timeout,
        capture_output=True,
    )


def run_step_with_fallback(
    step: Dict[str, Any],
    *,
    cwd: Path,
    env: Optional[Mapping[str, str]] = None,
    timeout_s: Optional[int] = None,
) -> StepResult:
    """
    Behavior:
    - Resolve intent -> preferred command and raw cmd
    - If resolved.source == 'raw' -> run raw and return
    - If resolved.source == 'firsttry' -> run FirstTry-native, on failure fall back to raw
    """
    step_id = str(step.get("id") or step.get("name") or "<unnamed>")
    resolved: ResolvedCommand = resolve_command_for_step(step)

    if resolved.source == "raw":
        try:
            cp = _run_shell(resolved.used_cmd, cwd=cwd, env=env, timeout=timeout_s)
            return StepResult(
                step_id=step_id,
                intent_key=resolved.intent_key,
                used_cmd=resolved.used_cmd,
                raw_cmd=resolved.raw_cmd,
                used_source="raw",
                fallback_used=False,
                returncode=cp.returncode,
                timed_out=False,
                timeout_s=timeout_s,
            )
        except subprocess.TimeoutExpired:
            print(f"STEP TIMEOUT: {step_id} after {timeout_s}s (raw cmd)")
            return StepResult(
                step_id=step_id,
                intent_key=resolved.intent_key,
                used_cmd=resolved.used_cmd,
                raw_cmd=resolved.raw_cmd,
                used_source="raw",
                fallback_used=False,
                returncode=124,
                timed_out=True,
                timeout_s=timeout_s,
            )

    # FirstTry-native first
    try:
        firsttry_cp = _run_shell(resolved.used_cmd, cwd=cwd, env=env, timeout=timeout_s)
        if firsttry_cp.returncode == 0:
            return StepResult(
                step_id=step_id,
                intent_key=resolved.intent_key,
                used_cmd=resolved.used_cmd,
                raw_cmd=resolved.raw_cmd,
                used_source="firsttry",
                fallback_used=False,
                returncode=0,
                timed_out=False,
                timeout_s=timeout_s,
            )
    except subprocess.TimeoutExpired:
        print(f"STEP TIMEOUT: {step_id} after {timeout_s}s (FirstTry-native cmd); falling back to raw")
        # treat as failure and fall through to fallback behavior
        firsttry_cp = None
    else:
        # if returned non-zero, we'll fall back below
        pass

    # If we get here, FirstTry either timed out or exited non-zero -> fallback to raw
    firsttry_rc = getattr(firsttry_cp, "returncode", None)
    print(
        f"[firsttry] WARN: intent '{resolved.intent_key}' step '{step_id}' "
        f"failed via FirstTry command '{resolved.used_cmd}' (exit={firsttry_rc}); "
        f"falling back to raw CI command '{resolved.raw_cmd}'."
    )

    try:
        raw_cp = _run_shell(resolved.raw_cmd, cwd=cwd, env=env, timeout=timeout_s)
        return StepResult(
            step_id=step_id,
            intent_key=resolved.intent_key,
            used_cmd=resolved.raw_cmd,
            raw_cmd=resolved.raw_cmd,
            used_source="raw",
            fallback_used=True,
            returncode=raw_cp.returncode,
            timed_out=False,
            timeout_s=timeout_s,
        )
    except subprocess.TimeoutExpired:
        print(f"STEP TIMEOUT: {step_id} after {timeout_s}s (raw cmd)")
        return StepResult(
            step_id=step_id,
            intent_key=resolved.intent_key,
            used_cmd=resolved.raw_cmd,
            raw_cmd=resolved.raw_cmd,
            used_source="raw",
            fallback_used=True,
            returncode=124,
            timed_out=True,
            timeout_s=timeout_s,
        )


def print_gate_plan_summary(plan_name: str, step_results: List[StepResult]) -> None:
    """
    Human-readable summary of how a plan ran:
    - which intent (if any) each step used
    - whether FirstTry or raw cmd was used
    - whether fallback was triggered
    """
    print(f"\n📋 Gate plan summary: {plan_name}")
    if not step_results:
        print("  (no steps)")
        return

    for r in step_results:
        origin = "FirstTry" if r.used_source == "firsttry" else "CI raw"
        fallback = " (fallback to raw used)" if r.fallback_used else ""
        intent = f"[intent={r.intent_key}]" if r.intent_key else "[no-intent]"
        status = "✅" if r.returncode == 0 else "❌"
        print(
            f"  {status} step={r.step_id} {intent}: "
            f"{origin} cmd=`{r.used_cmd}`{fallback}"
        )
