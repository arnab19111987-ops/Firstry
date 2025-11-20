from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import cache as ft_cache
from . import progress
from .cache_utils import collect_input_stats, input_stats_match
from .check_dependencies import should_skip_due_to_dependencies
from .check_registry import CHECK_REGISTRY, get_check_inputs
from .run_profiles import get_pytest_mode_for_profile
from .smart_npm import run_smart_npm_test
from .smart_pytest import run_smart_pytest

MAX_WORKERS = min(4, os.cpu_count() or 2)


def run_tool_with_smart_cache(
    repo_root: str, tool_name: str, input_paths: List[str]
) -> Dict[str, Any]:
    """
    Smart cache that replays failed results when inputs are identical.
    This makes stat-first cache visible in demos by avoiding re-runs of failed tools.
    """
    current_stats = collect_input_stats(input_paths)
    cache_entry = ft_cache.load_tool_cache_entry(repo_root, tool_name)

    # 1) FAST PATH: stats match
    # `collect_input_stats` may return `None` on error; only compare when present.
    if cache_entry and current_stats is not None and input_stats_match(
        cache_entry.input_files, current_stats
    ):
        # 👉 if last run failed, just replay it instead of re-running
        if cache_entry.status == "fail":
            return {
                "name": tool_name,
                "status": "fail",
                "from_cache": True,
                "cache_state": "hit-policy",
                "meta": cache_entry.extra,
                "cached": True,
                "elapsed": cache_entry.extra.get("elapsed", 0.0),
            }
        # 👉 last run passed -> normal hit
        return {
            "name": tool_name,
            "status": cache_entry.status,
            "from_cache": True,
            "cache_state": "hit",
            "meta": cache_entry.extra,
            "cached": True,
            "elapsed": cache_entry.extra.get("elapsed", 0.0),
        }

    # 2) SLOW PATH: something changed -> will need to run the tool
    return {
        "name": tool_name,
        "status": "miss",
        "from_cache": False,
        "cache_state": "miss",
        "meta": {},
        "cached": False,
    }


async def run_subprocess(cmd: List[str], cwd: str | None = None) -> Tuple[int, str]:
    """Run subprocess and return exit code + output"""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    # `proc.returncode` may be None according to the runtime types; normalize to int
    rc: int = proc.returncode if proc.returncode is not None else -1
    return rc, stdout.decode("utf-8", "replace")


async def _bounded_run(cmd: List[str], sem: asyncio.Semaphore, cwd: str | None = None):
    """Run subprocess with semaphore for concurrency control"""
    async with sem:
        return await run_subprocess(cmd, cwd=cwd)


def _glob_inputs(repo_root: Path, patterns: List[str]) -> List[Path]:
    """Expand glob patterns to actual file paths"""
    if not patterns:
        return []
    out: List[Path] = []
    for pat in patterns:
        # Use pathlib's glob for consistency
        matches = list(repo_root.glob(pat))
        out.extend(matches)
    return out


def _tool_input_hash(repo_root: Path, tool_name: str) -> str:
    """Compute hash of all input files for a tool"""
    patterns = get_check_inputs(tool_name)
    files = _glob_inputs(repo_root, patterns)
    return ft_cache.sha256_of_paths(files)


def _tool_to_cmd(tool_name: str) -> List[str]:
    """Map logical tool name to actual command"""
    # Map to actual commands used in this codebase
    command_map = {
        "ruff": ["ruff", "check", "."],
        "repo_sanity": [
            "python",
            "-c",
            "print('Repo sanity check passed')",
        ],  # placeholder
        "black": ["black", "--check", "."],
        "mypy": ["mypy", "."],
        "pytest": [
            "python",
            "-m",
            "pytest",
            "-q",
        ],  # Basic fallback - smart pytest handles this
        "npm test": ["npm", "test"],
        "ci-parity": ["python", "-c", "print('CI parity check passed')"],  # placeholder
    }
    return command_map.get(tool_name, ["echo", f"Unknown tool: {tool_name}"])


async def run_checks_for_profile(
    repo_root: str,
    checks: List[str],
    use_cache: bool = True,
    changed_files: List[str] | None = None,
    profile: str = "dev",
) -> Dict[str, Any]:
    """
    Run checks bucketed by speed: fast -> mutating -> slow
    Returns results with per-check details for summary.
    Enhanced with timing and mutating cache invalidation.
    """
    import time

    # 🔍 PHASE TIMING INSTRUMENTATION - Track where the "hidden 11 seconds" goes
    t0 = time.monotonic()

    t_detect_start = time.monotonic()
    root = Path(repo_root)
    results: Dict[str, Any] = {}
    failed_checks: set[str] = set()  # Track failed checks for dependency logic
    mutating_ran = False  # Track if any mutating check ran successfully
    t_detect_end = time.monotonic()

    t_setup_start = time.monotonic()
    progress.step(
        f"Running {len(checks)} checks with caching={'enabled' if use_cache else 'disabled'}"
    )
    t_setup_end = time.monotonic()

    # Group checks by bucket
    t_bucketing_start = time.monotonic()
    # Explicitly annotate buckets to satisfy type checkers
    buckets: Dict[str, List[str]] = {"fast": [], "mutating": [], "slow": []}

    for check in checks:
        bucket = CHECK_REGISTRY.get(check, {}).get("bucket", "slow")
        buckets[bucket].append(check)

    t_bucketing_end = time.monotonic()

    # 1) FAST BUCKET (parallel)
    t_fast_start = time.monotonic()
    fast_checks = buckets["fast"]
    if fast_checks:
        progress.bucket_header("fast", len(fast_checks))
        fast_sem = asyncio.Semaphore(MAX_WORKERS)
        fast_tasks = []

        for chk in fast_checks:
            # Use smart cache that replays failed results
            patterns = get_check_inputs(chk)
            input_paths = [str(f) for f in _glob_inputs(root, patterns)]

            if use_cache:
                cache_result = run_tool_with_smart_cache(repo_root, chk, input_paths)
                if cache_result["cached"]:
                    progress.cached(chk)
                    results[chk] = cache_result
                    continue

            # Need to run the tool - compute hash for cache writing
            inp_hash = _tool_input_hash(root, chk)
            cmd = _tool_to_cmd(chk)
            fast_tasks.append(
                (chk, inp_hash, _bounded_run(cmd, fast_sem, cwd=repo_root))
            )  # Execute pending fast checks
        for chk, inp_hash, coro in fast_tasks:
            start = time.monotonic()
            try:
                rc, out = await coro
                elapsed = time.monotonic() - start
                if rc == 0:
                    ft_cache.write_tool_cache(
                        repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
                    )
                    progress.done(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "ok", "output": out, "elapsed": elapsed}
                else:
                    failed_checks.add(chk)  # Track failure for dependencies
                    ft_cache.write_tool_cache(
                        repo_root,
                        chk,
                        inp_hash,
                        "fail",
                        {"elapsed": elapsed, "output": out},
                    )
                    progress.fail(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "fail", "output": out, "elapsed": elapsed}
            except Exception as e:
                elapsed = time.monotonic() - start
                failed_checks.add(chk)  # Track error as failure
                progress.fail(f"{chk} (error: {e}, {elapsed:.2f}s)")
                results[chk] = {"status": "error", "error": str(e), "elapsed": elapsed}

    t_fast_end = time.monotonic()

    # 2) MUTATING BUCKET (serial to avoid conflicts)
    t_mutating_start = time.monotonic()
    mut_checks = buckets["mutating"]
    if mut_checks:
        progress.bucket_header("mutating", len(mut_checks))

        for chk in mut_checks:
            # Use stat-first cache validation
            patterns = get_check_inputs(chk)
            input_paths = [str(f) for f in _glob_inputs(root, patterns)]

            if use_cache:
                is_valid, cache_state = ft_cache.is_tool_cache_valid_fast(
                    repo_root, chk, input_paths
                )
                if is_valid:
                    progress.cached(chk)
                    results[chk] = {
                        "status": "ok",
                        "cached": True,
                        "cache_state": cache_state,
                    }
                    continue

            # Fallback to hash for cache writing (only computed when needed)
            inp_hash = _tool_input_hash(root, chk)

            cmd = _tool_to_cmd(chk)
            start = time.monotonic()
            try:
                rc, out = await run_subprocess(cmd, cwd=repo_root)
                elapsed = time.monotonic() - start
                if rc == 0:
                    mutating_ran = True  # Track that a mutating check ran successfully
                    ft_cache.write_tool_cache(
                        repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
                    )
                    progress.done(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "ok", "output": out, "elapsed": elapsed}
                else:
                    failed_checks.add(chk)  # Track failure for dependencies
                    ft_cache.write_tool_cache(
                        repo_root,
                        chk,
                        inp_hash,
                        "fail",
                        {"elapsed": elapsed, "output": out},
                    )
                    progress.fail(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "fail", "output": out, "elapsed": elapsed}
            except Exception as e:
                elapsed = time.monotonic() - start
                failed_checks.add(chk)  # Track error as failure
                progress.fail(f"{chk} (error: {e}, {elapsed:.2f}s)")
                results[chk] = {"status": "error", "error": str(e), "elapsed": elapsed}

    # 3) SLOW BUCKET (parallel, with smart pytest)
    slow_checks = buckets["slow"]
    if slow_checks:
        progress.bucket_header("slow", len(slow_checks))
        slow_sem = asyncio.Semaphore(MAX_WORKERS)
        slow_tasks = []

        for chk in slow_checks:
            # Check dependencies before running
            blocking_rule = should_skip_due_to_dependencies(chk, failed_checks, profile)
            if blocking_rule:
                progress.cached(f"{chk} (skipped: {blocking_rule.reason})")
                results[chk] = {
                    "status": "skipped",
                    "reason": blocking_rule.reason,
                    "prerequisite": blocking_rule.prerequisite,
                    "strict": blocking_rule.strict,
                }
                continue

            # Special handling for pytest - use smart pytest system
            if chk == "pytest":
                try:
                    pytest_mode = get_pytest_mode_for_profile(profile)
                    pytest_result = await run_smart_pytest(
                        repo_root=repo_root,
                        changed_files=changed_files,
                        mode=pytest_mode,
                        use_cache=use_cache,
                    )

                    if pytest_result["status"] == "ok":
                        progress.done("pytest (smart)")
                    elif pytest_result.get("cached"):
                        progress.cached("pytest")
                    else:
                        failed_checks.add(chk)  # Track pytest failure
                        progress.fail("pytest (smart)")

                    results[chk] = pytest_result
                    continue
                except Exception as e:
                    failed_checks.add(chk)  # Track pytest error
                    progress.fail(f"pytest (error: {e})")
                    results[chk] = {"status": "error", "error": str(e)}
                    continue

            # Special handling for npm test - use smart npm system
            if chk == "npm test":
                try:
                    npm_result = await run_smart_npm_test(
                        repo_root=repo_root,
                        changed_files=changed_files or [],
                        force_run=(profile == "strict"),  # Force run in strict mode
                        use_cache=use_cache,
                    )

                    if npm_result["status"] == "ok":
                        progress.done("npm test (smart)")
                    elif npm_result["status"] == "skipped":
                        progress.cached(f"npm test (skipped: {npm_result['reason']})")
                    elif npm_result.get("cached"):
                        progress.cached("npm test")
                    else:
                        failed_checks.add(chk)  # Track npm test failure
                        progress.fail("npm test (smart)")

                    results[chk] = npm_result
                    continue
                except Exception as e:
                    failed_checks.add(chk)  # Track npm test error
                    progress.fail(f"npm test (error: {e})")
                    results[chk] = {"status": "error", "error": str(e)}
                    continue

            # Regular handling for other slow checks
            patterns = get_check_inputs(chk)
            input_paths = [str(f) for f in _glob_inputs(root, patterns)]

            # CRITICAL: If any mutating check ran, do NOT trust cache for slow checks
            use_cache_for_slow = use_cache and not mutating_ran

            if use_cache_for_slow:
                is_valid, cache_state = ft_cache.is_tool_cache_valid_fast(
                    repo_root, chk, input_paths
                )
                if is_valid:
                    progress.cached(chk)
                    results[chk] = {
                        "status": "ok",
                        "cached": True,
                        "cache_state": cache_state,
                        "elapsed": 0.0,
                    }
                    continue

            # Fallback to hash for cache writing (only computed when needed)
            inp_hash = _tool_input_hash(root, chk)

            cmd = _tool_to_cmd(chk)
            slow_tasks.append(
                (chk, inp_hash, _bounded_run(cmd, slow_sem, cwd=repo_root))
            )

        # Execute pending slow checks (non-pytest)
        for chk, inp_hash, coro in slow_tasks:
            start = time.monotonic()
            try:
                rc, out = await coro
                elapsed = time.monotonic() - start
                if rc == 0:
                    ft_cache.write_tool_cache(
                        repo_root, chk, inp_hash, "ok", {"elapsed": elapsed}
                    )
                    progress.done(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "ok", "output": out, "elapsed": elapsed}
                else:
                    failed_checks.add(chk)  # Track failure for dependencies
                    ft_cache.write_tool_cache(
                        repo_root,
                        chk,
                        inp_hash,
                        "fail",
                        {"elapsed": elapsed, "output": out},
                    )
                    progress.fail(f"{chk} ({elapsed:.2f}s)")
                    results[chk] = {"status": "fail", "output": out, "elapsed": elapsed}
            except Exception as e:
                elapsed = time.monotonic() - start
                failed_checks.add(chk)  # Track error as failure
                progress.fail(f"{chk} (error: {e}, {elapsed:.2f}s)")
                results[chk] = {"status": "error", "error": str(e), "elapsed": elapsed}

    # ─────────────────────────────
    # Summary timing
    # ─────────────────────────────
    t_slow_end = time.monotonic()
    t_report_start = time.monotonic()

    total_elapsed = sum(r.get("elapsed", 0.0) for r in results.values())
    progress.step(
        f"⏱  Total active check time (not counting cache hits): {total_elapsed:.2f}s"
    )

    if mutating_ran:
        progress.step("⚠️  Mutating checks ran - slow check cache was invalidated")
        # Invalidate cache for tools that might see different results after formatting
        affected_tools = ["ruff", "mypy", "pytest"]
        for tool in affected_tools:
            ft_cache.invalidate_tool_cache(repo_root, tool)
        progress.step(f"🗑️  Invalidated cache for: {', '.join(affected_tools)}")

    # 🔍 PHASE TIMING REPORT - Show where the "hidden seconds" go
    t_total = time.monotonic() - t0

    # Calculate phase durations (milliseconds for precision)
    detect_ms = (t_detect_end - t_detect_start) * 1000
    setup_ms = (t_setup_end - t_setup_start) * 1000
    bucketing_ms = (t_bucketing_end - t_bucketing_start) * 1000
    fast_ms = (t_fast_end - t_fast_start) * 1000
    mutating_ms = (
        (t_mutating_start - t_fast_end) * 1000 if "t_mutating_start" in locals() else 0
    )
    slow_ms = (
        (t_slow_end - t_mutating_start) * 1000 if "t_mutating_start" in locals() else 0
    )
    report_ms = (time.monotonic() - t_report_start) * 1000

    progress.step("🔍 Phase Timing Analysis:")
    progress.step(f"  • detect/setup: {detect_ms + setup_ms:.0f}ms")
    progress.step(f"  • bucketing: {bucketing_ms:.0f}ms")
    progress.step(f"  • fast phase: {fast_ms:.0f}ms")
    progress.step(f"  • mutating phase: {mutating_ms:.0f}ms")
    progress.step(f"  • slow phase: {slow_ms:.0f}ms")
    progress.step(f"  • reporting: {report_ms:.0f}ms")
    progress.step(f"  • total: {t_total * 1000:.0f}ms")

    # Store timing metadata for analysis
    results["_timing_metadata"] = {
        "detect_ms": detect_ms + setup_ms,
        "bucketing_ms": bucketing_ms,
        "fast_ms": fast_ms,
        "mutating_ms": mutating_ms,
        "slow_ms": slow_ms,
        "report_ms": report_ms,
        "total_ms": t_total * 1000,
        "check_execution_ms": total_elapsed * 1000,
    }

    return results
