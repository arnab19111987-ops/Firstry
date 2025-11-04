# src/firsttry/checks_orchestrator.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .profiler import get_profiler


async def _timed_runner_execution(runner, worker_id: int, ctx: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a runner with timing instrumentation."""
    profiler = get_profiler()
    family = _family_of(item)
    tool = item.get("tool") or family
    
    # Start timing
    profiler.start_check(tool, family)
    
    try:
        result = await runner.run(worker_id, ctx, item)
        
        # Determine success/exit code from result
        if isinstance(result, dict):
            success = result.get("ok", True)
            exit_code = 0 if success else 1
        else:
            success = True
            exit_code = 0
        
        # End timing
        duration = profiler.end_check(tool, family, exit_code, success)
        
        # Add timing info to result
        if isinstance(result, dict):
            result["duration"] = duration
        else:
            result = {"ok": True, "result": result, "duration": duration}
        
        return result
        
    except Exception as e:
        # End timing with error
        profiler.end_check(tool, family, 1, False)
        raise e


# Prefer the package's RUNNERS; if unavailable, fall back to an empty dict.
# Tests will monkeypatch this symbol directly inside this module.
try:
    from .runners import RUNNERS  # type: ignore
except Exception:  # pragma: no cover
    RUNNERS = {}  # type: ignore


# ---- BUCKET DEFINITIONS -------------------------------------------------

FAST_FAMILIES = {
    "ruff",
    "mypy",
    "pylint",
    "bandit",
    "safety",
    "pyright",
}

MUTATING_FAMILIES = {
    "black",
    "black-fix",
    "ruff-fix",
    "isort",
    "autoflake",
    "autofix",
}

SLOW_FAMILIES = {
    "pytest",
    "pytest-strict",
    "npm",
    "npm-test",
    "npm test",
    "ci-parity",
    "ci_parity",
}


def _family_of(item: Any) -> str:
    """Extract family/tool name from item (supports both dict and string)."""
    if isinstance(item, str):
        return item
    elif isinstance(item, dict):
        return item.get("family") or item.get("tool") or item.get("name") or ""
    else:
        return str(item)


def _bucketize(plan: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    fast: List[Dict[str, Any]] = []
    mutating: List[Dict[str, Any]] = []
    slow: List[Dict[str, Any]] = []
    other: List[Dict[str, Any]] = []

    for item in plan:
        family = _family_of(item)
        if family in MUTATING_FAMILIES:
            mutating.append(item)
        elif family in FAST_FAMILIES:
            fast.append(item)
        elif family in SLOW_FAMILIES:
            slow.append(item)
        else:
            other.append(item)

    return {
        "fast": fast,
        "mutating": mutating,
        "other": other,
        "slow": slow,
    }


# ---- CORE BUCKET RUNNER -------------------------------------------------


async def _run_bucket_with_timeout(
    bucket: List[Dict[str, Any]],
    allocation: Dict[str, int],
    ctx: Dict[str, Any],
    tier: Optional[str],
    config: Optional[Dict[str, Any]],
    timeout_seconds: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Run a bucket of checks with individual timeouts.
    Uses asyncio with timeout instead of ProcessPoolExecutor for simpler implementation.
    """
    if not bucket:
        return []
    
    tasks = []
    task_to_item = {}
    
    for item in bucket:
        family = _family_of(item)
        tool = item.get("tool") or family
        workers = allocation.get(family, 1)
        
        runner = RUNNERS.get(tool)
        if not runner:
            # custom command runner
            if item.get("cmd"):
                runner = RUNNERS["custom"]
            else:
                # nothing we can run for this item
                continue
        
        # create up to N tasks for this family
        for i in range(max(1, workers)):
            # Wrap with timeout - capture all loop variables to avoid closure bug
            async def run_with_timeout(captured_item=item, captured_family=family, captured_tool=tool, captured_runner=runner, worker_id=i):
                try:
                    return await asyncio.wait_for(
                        _timed_runner_execution(captured_runner, worker_id, ctx, captured_item),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    return {
                        "ok": False,
                        "family": captured_family,
                        "tool": captured_tool,
                        "error": f"Timed out after {timeout_seconds}s",
                    }
            
            t = asyncio.create_task(run_with_timeout())
            tasks.append(t)
            task_to_item[t] = item
    
    if not tasks:
        return []
    
    finished = await asyncio.gather(*tasks, return_exceptions=True)
    
    results = []
    for task, out in zip(tasks, finished):
        item = task_to_item[task]
        family = _family_of(item)
        
        if isinstance(out, Exception):
            results.append({
                "ok": False,
                "family": family,
                "tool": item.get("tool") or family,
                "error": str(out),
            })
        else:
            # ensure the runner result is a dict and contains family/tool
            if not isinstance(out, dict):
                out = {"ok": True, "result": out}
            out.setdefault("family", family)
            out.setdefault("tool", item.get("tool") or family)
            results.append(out)
    
    return results


async def _run_bucket(
    bucket: List[Dict[str, Any]],
    allocation: Dict[str, int],
    ctx: Dict[str, Any],
    tier: Optional[str],
    config: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Run bucket with timeout support.
    """
    # Different timeout for different bucket types
    family_names = [_family_of(item) for item in bucket]
    
    # SLOW checks get longer timeout
    slow_families = {"pytest", "npm", "ci-parity"}
    if any(f in slow_families for f in family_names):
        timeout = 60.0  # 60s for slow checks
    else:
        timeout = 30.0  # 30s for fast checks
    
    return await _run_bucket_with_timeout(bucket, allocation, ctx, tier, config, timeout)


# ---- PUBLIC ENTRYPOINT (USED BY CLI) ------------------------------------


async def run_orchestrator(
    allocation: Dict[str, int],
    plan: List[Dict[str, Any]],
    ctx: Dict[str, Any],
    tier: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    show_phases: bool = False,
) -> Dict[str, Any]:
    """
    Bucketed orchestrator.
    Runs checks in phases:
    1) FAST (parallel)
    2) MUTATING (serial, conflict-avoidance)
    3) OTHER (parallel)
    4) SLOW (parallel, last for fast feedback)
    """
    # Reset profiler for this run
    from .profiler import reset_profiler
    reset_profiler()

    if not plan:
        return {"ok": True, "checks": []}

    buckets = _bucketize(plan)
    all_results: List[Dict[str, Any]] = []

    # 1) fast → parallel (gives immediate feedback)
    if buckets["fast"]:
        if show_phases:
            print("⚡ firsttry: running FAST checks in parallel:", ", ".join(_family_of(i) for i in buckets["fast"]))
        fast_results = await _run_bucket(buckets["fast"], allocation, ctx, tier, config)
        all_results.extend(fast_results)

    # 2) mutating → serial (avoids file conflicts)
    if buckets["mutating"]:
        if show_phases:
            print("→ firsttry: running MUTATING checks serially:", ", ".join(_family_of(i) for i in buckets["mutating"]))
        for item in buckets["mutating"]:
            mut_res = await _run_bucket([item], allocation, ctx, tier, config)
            all_results.extend(mut_res)

    # 3) other → parallel (safe default)
    if buckets["other"]:
        if show_phases:
            print("→ firsttry: running OTHER checks in parallel:", ", ".join(_family_of(i) for i in buckets["other"]))
        other_results = await _run_bucket(buckets["other"], allocation, ctx, tier, config)
        all_results.extend(other_results)

    # 4) slow → parallel, but last so users see quick wins first
    if buckets["slow"]:
        if show_phases:
            print("⏳ firsttry: running SLOW checks in parallel:", ", ".join(_family_of(i) for i in buckets["slow"]))
        slow_results = await _run_bucket(buckets["slow"], allocation, ctx, tier, config)
        all_results.extend(slow_results)

    ok = all(r.get("ok", True) for r in all_results)

    # Print timing summary
    profiler = get_profiler()
    profiler.print_timing_summary()

    return {
        "ok": ok,
        "checks": all_results,
    }


# Alias for backward compatibility
run_checks_with_allocation_and_plan = run_orchestrator

