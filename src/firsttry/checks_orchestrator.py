# src/firsttry/checks_orchestrator.py
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from .profiler import get_profiler

# soft imports / fallbacks: allow orchestrator to be imported even if
# agent_manager or config_loader move around during refactors.
try:
    from firsttry.agent_manager import SmartAgentManager  # type: ignore
except Exception:  # pragma: no cover - fallback for analysis tools
    class SmartAgentManager:  # type: ignore
        @classmethod
        def from_context(cls, cpu_hint=None):
            return cls()

        def allocate_for_plan(self, plan):
            # default: 1 worker per family
            alloc = {}
            for p in plan:
                fam = (p.get("family") or "").strip().lower()
                alloc[fam] = max(1, alloc.get(fam, 0))
            return alloc

try:
    from firsttry.config_loader import load_config  # type: ignore
except Exception:
    def load_config(_):  # type: ignore
        return {}

# Bandit JSON runner
try:
    from .checks.bandit_runner import run_bandit_json, evaluate_bandit
except Exception:
    # graceful fallback if module not importable
    run_bandit_json = None
    evaluate_bandit = None

# Sharded bandit runner (faster for large repos)
try:
    from .checks.bandit_sharded import BanditConfig, run_bandit_sharded
except Exception:
    BanditConfig = None
    run_bandit_sharded = None


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


# NOTE:
# In your current repo this was already imported from somewhere.
# Keep the import that already exists. If your existing file says
# `from .runners import RUNNERS`, keep that.
try:  # safe fallback so copy-paste doesn't explode
    from .runners import RUNNERS  # type: ignore
except Exception:  # pragma: no cover
    # fallback stub if runners package isn't importable during static analysis
    RUNNERS = {}


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

    # Map generic families produced by plan builders to canonical bucket families
FAMILY_ALIASES = {
    "tests": "pytest",
    "lint": "ruff",
    "type": "mypy",
    "security": "bandit",
    # default - may be adjusted dynamically below
    "deps": "safety",
}

# Prefer the deps runner that exists in the loaded RUNNERS mapping.
# Use pip-audit if available, otherwise fall back to safety.
try:
    if "pip-audit" in RUNNERS:
        FAMILY_ALIASES["deps"] = "pip-audit"
    elif "safety" in RUNNERS:
        FAMILY_ALIASES["deps"] = "safety"
    else:
        FAMILY_ALIASES["deps"] = FAMILY_ALIASES.get("deps", "safety")
except Exception:
    # conservative default
    FAMILY_ALIASES["deps"] = FAMILY_ALIASES.get("deps", "safety")


def _norm_family(item: Any) -> str:
    """Return canonical family name for an item, applying aliases.

    This helper centralizes normalization so callers can rely on a
    consistent canonical family string for bucket membership checks.
    """
    raw = ""
    if isinstance(item, dict):
        raw = (item.get("family") or _family_of(item) or "").strip().lower()
    else:
        raw = str(item).strip().lower()
    return FAMILY_ALIASES.get(raw, raw)

def _family_of(item: Any) -> str:
    """Extract family/tool name from item (supports both dict and string)."""
    if isinstance(item, str):
        return item
    elif isinstance(item, dict):
        return item.get("family") or item.get("tool") or item.get("name") or ""
    else:
        return str(item)


def _pyproj_cfg(cfg: Optional[Dict[str, Any]], path: str, key: str, default=None):
    # safe nested accessor in case pyproject mapping shape varies
    try:
        return cfg.get(path, {}).get(key, default) if isinstance(cfg, dict) else default
    except Exception:
        return default


# Per-family worker caps (enforced after allocation)
# keys may be tool-only (e.g. 'ruff') or family:tool (e.g. 'python:ruff')
FAMILY_WORKER_CAPS: Dict[str, int] = {
    "ruff": 1,
    "mypy": 1,
    "pytest": 2,
    "bandit": 2,
}

# runtime-adjustable caps loaded from config [tool.firsttry.runner.caps]
RUNNER_CAPS: Dict[str, int] = {}


def _cap_workers(family: str, tool: str, workers: int) -> int:
    """Apply per-family/tool caps to the requested worker count."""
    if not family and not tool:
        return workers
    key1 = f"{family}:{tool}".lower()
    key2 = (tool or "").lower()
    key3 = (family or "").lower()
    # config-specified caps take precedence
    for k in (key1, key2, key3):
        if k in RUNNER_CAPS:
            return min(workers, int(RUNNER_CAPS[k]))
    for k in (key1, key2, key3):
        if k in FAMILY_WORKER_CAPS:
            return min(workers, FAMILY_WORKER_CAPS[k])
    return workers


def _bandit_cfg_from_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the bandit config regardless of whether `config` is the full
    pyproject mapping (with a `tool.firsttry` nested table) or the already-
    extracted `tool.firsttry` dict that `load_config()` returns.
    """
    if not config or not isinstance(config, dict):
        return {}

    # Case A: full pyproject mapping (tool.firsttry.checks.bandit)
    try:
        tool = config.get("tool")
        if isinstance(tool, dict) and isinstance(tool.get("firsttry"), dict):
            return tool.get("firsttry", {}).get("checks", {}).get("bandit", {}) or {}
    except Exception:
        pass

    # Case B: config is already the tool.firsttry mapping (returned by load_config())
    try:
        return config.get("checks", {}).get("bandit", {}) or {}
    except Exception:
        return {}


def register_bandit_check(config: Optional[Dict[str, Any]], repo_root: Path, report_dir: Path, results: List[Dict[str, Any]]):
    """
    Adds/runs the Bandit check using JSON, respecting pyproject overrides:
    [tool.firsttry.checks.bandit]
    fail_on = "high" | "medium" | "low" | "critical"
    blocking = true | false
    enabled = true | false
    """
    if run_bandit_json is None or evaluate_bandit is None:
        # Bandit runner not available; mark as skipped
        results.append({
            "ok": True,
            "family": "bandit",
            "tool": "bandit",
            "result": SimpleNamespace(message="bandit runner unavailable"),
            "duration": 0.0,
        })
        return

    # read nested config at [tool.firsttry.checks.bandit]
    bandit_cfg = _bandit_cfg_from_config(config)

    enabled = bandit_cfg.get("enabled", True)
    if not enabled:
        results.append({
            "ok": True,
            "family": "bandit",
            "tool": "bandit",
            "result": SimpleNamespace(message="disabled via config"),
            "duration": 0.0,
        })
        return

    fail_on = (bandit_cfg.get("fail_on") or "high").lower()
    blocking = bool(bandit_cfg.get("blocking", True))
    out_json = Path(report_dir) / "bandit.json"
    res = run_bandit_json(repo_root, out_json)
    cr = evaluate_bandit(res, fail_on=fail_on, blocking=blocking)

    # Normalize into orchestrator result shape
    ok = cr.status == "pass"
    if cr.status == "advisory":
        # advisory counts as ok for pipeline-level gating but we surface details
        ok = True

    results.append({
        "ok": ok,
        "family": "bandit",
        "tool": "bandit",
        "result": SimpleNamespace(message=json.dumps(cr.details)),
        "duration": 0.0,
    })


def _bucketize(plan: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    fast: List[Dict[str, Any]] = []
    mutating: List[Dict[str, Any]] = []
    slow: List[Dict[str, Any]] = []
    other: List[Dict[str, Any]] = []

    for item in plan:
        # normalize family names and apply aliases so buckets match expected names
        raw = (item.get("family") or _family_of(item) or "").strip().lower()
        fam = FAMILY_ALIASES.get(raw, raw)
        if fam in MUTATING_FAMILIES:
            mutating.append(item)
        elif fam in FAST_FAMILIES:
            fast.append(item)
        elif fam in SLOW_FAMILIES:
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
        # Keep allocation lookup using the original family key (allocator expects that),
        # but determine canonical family (via _norm_family) when checking mutating membership.
        family = (item.get("family") or "").lower()
        tool = item.get("tool") or family
        workers = max(1, allocation.get(family, 1))
        canonical = _norm_family(item)
        # Hard clamp for safety: never allow >1 concurrent workers for mutating families
        if canonical in MUTATING_FAMILIES:
            workers = 1
        # Apply configured per-family caps (ruff=1, mypy=1, pytest<=2, bandit<=2)
        workers = _cap_workers(family, tool, workers)
        for i in range(workers):
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

    # Create a shared global semaphore for bounded concurrency across all runners.
    # Config may optionally include [runner].max_workers to override CPU-based default.
    try:
        max_workers_cfg = 0
        if isinstance(config, dict) and config.get("runner"):
            max_workers_cfg = int((config.get("runner") or {}).get("max_workers", 0) or 0)
    except Exception:
        max_workers_cfg = 0

    import threading
    cpu = os.cpu_count() or 4
    limit = cpu if max_workers_cfg in (0, None) else max(1, max_workers_cfg)
    # create the async semaphore instance and expose it to runners via ctx
    SEM = asyncio.Semaphore(limit)
    ctx.setdefault("global_semaphore", SEM)
    # Also expose a sync semaphore for synchronous helpers (scanner) to respect same cap
    try:
        from firsttry.runners import base as runners_base

        runners_base.GLOBAL_SYNC_SEMAPHORE = threading.Semaphore(limit)
    except Exception:
        # best-effort: if import fails, skip sync semaphore wiring
        pass

    if not plan:
        return {"ok": True, "checks": []}

    buckets = _bucketize(plan)
    # Load per-runner caps from config if provided (tool.firsttry.runner.caps)
    try:
        cfg_caps = (config or {}).get("runner", {}).get("caps", {}) if isinstance(config, dict) else {}
        if isinstance(cfg_caps, dict):
            # normalize keys to lowercase
            for k, v in cfg_caps.items():
                try:
                    RUNNER_CAPS[k.lower()] = int(v)
                except Exception:
                    pass
    except Exception:
        pass
    all_results: List[Dict[str, Any]] = []

    # 1) fast → parallel (gives immediate feedback)
    if buckets["fast"]:
        if show_phases:
            print("⚡ firsttry: running FAST checks in parallel:", ", ".join(_norm_family(i) for i in buckets["fast"]))
        fast_results = await _run_bucket(buckets["fast"], allocation, ctx, tier, config)
        all_results.extend(fast_results)

    # 2) mutating → serial (avoids file conflicts)
    if buckets["mutating"]:
        if show_phases:
            print("→ firsttry: running MUTATING checks serially:", ", ".join(_norm_family(i) for i in buckets["mutating"]))
        for item in buckets["mutating"]:
            # Shadow allocation so this item's family is clamped to 1
            orig_fam = (item.get("family") or "").lower()
            alloc1 = dict(allocation)
            alloc1[orig_fam] = 1
            res = await _run_bucket([item], alloc1, ctx, tier, config)
            all_results.extend(res)

    # 3) other → parallel (safe default)
    if buckets["other"]:
        if show_phases:
            print("→ firsttry: running OTHER checks in parallel:", ", ".join(_norm_family(i) for i in buckets["other"]))
        other_results = await _run_bucket(buckets["other"], allocation, ctx, tier, config)
        all_results.extend(other_results)

    # 4) slow → parallel, but last so users see quick wins first
    if buckets["slow"]:
        if show_phases:
            print("⏳ firsttry: running SLOW checks in parallel:", ", ".join(_norm_family(i) for i in buckets["slow"]))
        slow_results = await _run_bucket(buckets["slow"], allocation, ctx, tier, config)
        all_results.extend(slow_results)

    # If plan requested bandit, run the JSON-based bandit check (respects pyproject)
    try:
        if any((_family_of(i) == "bandit" or (isinstance(i, dict) and i.get("tool") == "bandit")) for i in plan):
            # Remove any existing bandit entries produced by legacy runners
            all_results = [r for r in all_results if not (r.get("tool") == "bandit" or r.get("family") == "bandit")]
            # report_dir: use .firsttry under repo root
            report_dir = Path(ctx.get("repo_root", ".")) / ".firsttry"
            # Prefer the sharded bandit runner when available
            if run_bandit_sharded is not None and BanditConfig is not None:
                bandit_cfg = _bandit_cfg_from_config(config)

                enabled = bool(bandit_cfg.get("enabled", True))
                if enabled:
                    default_include = ["src"] if (Path(ctx.get("repo_root", ".")) / "src").exists() else [""]
                    include = list(bandit_cfg.get("include", default_include))
                    exclude = list(bandit_cfg.get("exclude", [".venv","node_modules",".git","__pycache__","build","dist"]))
                    jobs = int(bandit_cfg.get("jobs", 0) or 0)
                    fail_on = str(bandit_cfg.get("fail_on", "high")).lower()
                    blocking = bool(bandit_cfg.get("blocking", True))
                    extra_args = list(bandit_cfg.get("extra_args", []))

                    cfg = BanditConfig(
                        include_dirs=include,
                        exclude_dirs=exclude,
                        jobs=jobs,
                        fail_on=fail_on,
                        blocking=blocking,
                        extra_args=extra_args,
                    )
                    out_json = report_dir / "bandit.json"
                    t0 = perf_counter()
                    agg = run_bandit_sharded(Path(ctx.get("repo_root", ".")), out_json, cfg)
                    dur = perf_counter() - t0

                    # evaluate
                    order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                    max_sev = agg.max_severity
                    meets_threshold = (order.get(str(max_sev or "").lower(), 0) >= order.get(fail_on, 0))

                    if agg.issues_total == 0 or not max_sev:
                        status = "pass"
                        reason = "No issues identified"
                    else:
                        if meets_threshold:
                            status = "fail" if blocking else "advisory"
                            reason = f"Max severity {max_sev} >= fail_on {fail_on}"
                        else:
                            status = "pass"
                            reason = f"Max severity {max_sev} < fail_on {fail_on}"

                    results_entry = {
                        "ok": status in ("pass", "advisory"),
                        "family": "bandit",
                        "tool": "bandit",
                        "result": SimpleNamespace(message=json.dumps({
                            "issues_total": agg.issues_total,
                            "by_severity": agg.by_severity,
                            "max_severity": agg.max_severity,
                            "raw_json": str(agg.raw_json_path),
                            "blocking": blocking,
                            "fail_on": fail_on,
                            "reason": reason,
                            "sharded": True,
                            "jobs": cfg.jobs or (os.cpu_count() or 2),
                            "include": include,
                            "exclude": exclude,
                        })),
                        "duration": float(dur),
                    }
                    all_results.append(results_entry)
                else:
                    all_results.append({
                        "ok": True,
                        "family": "bandit",
                        "tool": "bandit",
                        "result": SimpleNamespace(message="disabled via config"),
                        "duration": 0.0,
                    })
                # end sharded path
            else:
                register_bandit_check(config, Path(ctx.get("repo_root", ".")), report_dir, all_results)
    except Exception:
        # if anything goes wrong, don't block orchestrator
        pass

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

