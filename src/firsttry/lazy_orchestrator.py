from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from .cache import load_tool_cache_entry, save_tool_cache_entry
from .cache_models import ToolCacheEntry
from .cache_utils import collect_input_stats, input_stats_match
from .detectors import detect_stack
from .run_profiles import RunProfile, dev_profile


def _normalize_results_flat(raw: Any) -> List[Dict[str, Any]]:
    """
    Flatten nested results (e.g., [dict, [dict, dict]]) to List[dict],
    and ensure each dict has a 'status' key. 'skipped'/'noop' map to exit_code=0.
    """
    out: List[Dict[str, Any]] = []

    def _coerce(d: Dict[str, Any]) -> Dict[str, Any]:
        # Guarantee a status
        if "status" not in d:
            if "exit_code" in d:
                d["status"] = "ok" if d.get("exit_code", 1) == 0 else "error"
            elif "ok" in d:
                d["status"] = "ok" if d.get("ok") else "error"
            elif d.get("error"):
                d["status"] = "error"
            else:
                d["status"] = "unknown"
        # Non-failing semantics for skipped/noop
        if d.get("status") in ("skipped", "noop") and "exit_code" not in d:
            d["exit_code"] = 0
        return d

    def walk(v: Any) -> None:
        if isinstance(v, (list, tuple)):
            for i in v:
                walk(i)
        elif isinstance(v, dict):
            out.append(_coerce(v))
        else:
            out.append({"status": "unknown", "value": v, "exit_code": 0})

    walk(raw)
    return out


def run_tool_with_smart_cache(repo_root: Path, tool) -> dict[str, Any]:
    """Uses stat-first cache and replays failed results for demo visibility.
    Fixed to show 0.0s for cached tools and preserve old durations for analytics.
    """
    input_paths = tool.input_paths()
    current_stats = collect_input_stats(input_paths)
    cache_entry = load_tool_cache_entry(str(repo_root), tool.name)

    # FAST PATH: stats match => we can reuse
    if cache_entry and current_stats and input_stats_match(cache_entry.input_files, current_stats):
        # Get the last real duration for analytics
        last_duration = cache_entry.extra.get("elapsed", 0.0)
        exit_code = cache_entry.extra.get("exit_code", 0 if cache_entry.status == "ok" else 1)

        # replay failed => visible fast run
        if cache_entry.status == "fail":
            return {
                "name": tool.name,
                "status": "fail",
                "from_cache": True,
                "cache_state": "hit-policy",
                "meta": cache_entry.extra,
                "duration_s": 0.0,  # cached -> always 0
                "last_duration_s": last_duration,  # preserve for analytics
                "exit_code": exit_code,
            }
        return {
            "name": tool.name,
            "status": cache_entry.status,
            "from_cache": True,
            "cache_state": "hit",
            "meta": cache_entry.extra,
            "duration_s": 0.0,  # cached -> always 0
            "last_duration_s": last_duration,  # preserve for analytics
            "exit_code": exit_code,
        }

    # SLOW PATH: something changed -> run the tool
    start_time = time.monotonic()
    status, meta = tool.run()
    duration_s = time.monotonic() - start_time

    # Update meta with timing
    meta["elapsed"] = duration_s
    exit_code = meta.get("exit_code", 0 if status == "ok" else 1)

    # Save to cache (only if we have valid stats)
    if current_stats is not None:
        entry = ToolCacheEntry(
            tool_name=tool.name,
            input_files=current_stats,
            input_hash="",  # We use stat-first, hash not needed
            status=status,
            created_at=time.time(),
            extra=meta,
        )
        save_tool_cache_entry(str(repo_root), entry)

    return {
        "name": tool.name,
        "status": status,
        "from_cache": False,
        "cache_state": "miss",
        "meta": meta,
        "duration_s": duration_s,
        "exit_code": exit_code,
    }


def _run_tools(repo_root: Path, tools: list[Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for t in tools:
        res = run_tool_with_smart_cache(repo_root, t)
        results.append(res)
    return results


def run_profile_for_repo(
    repo_root: Path,
    profile: RunProfile | None = None,
    report_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Main orchestrator with LAZY bucket build.
    Only builds and runs what's needed when it's needed.
    """
    start_time = time.monotonic()

    # 1) detect (cached)
    t_detect_start = time.monotonic()
    detect_info = detect_stack(repo_root)
    t_detect_end = time.monotonic()

    # 2) choose profile
    if profile is None:
        profile = dev_profile()  # default

    # 3) FAST ONLY - build and run immediately
    fast_tools = profile.fast(repo_root)
    t_fast_start = time.monotonic()
    fast_results = _run_tools(repo_root, fast_tools)
    t_fast_end = time.monotonic()

    results: list[dict[str, Any]] = []
    results.extend(fast_results)

    # 4) decide if we need MUTATING - lazy build
    mutating_results = []
    t_mutating_start = time.monotonic()
    t_mutating_end = t_mutating_start  # default if no mutating
    if profile.has_mutating:
        mutating_tools = profile.mutating(repo_root)
        t_mutating_start = time.monotonic()
        mutating_results = _run_tools(repo_root, mutating_tools)
        t_mutating_end = time.monotonic()
        results.extend(mutating_results)

    # 5) decide if we need SLOW - lazy build
    slow_results = []
    t_slow_start = time.monotonic()
    t_slow_end = t_slow_start  # default if no slow
    if profile.has_slow:
        slow_tools = profile.slow(repo_root)
        t_slow_start = time.monotonic()
        slow_results = _run_tools(repo_root, slow_tools)
        t_slow_end = time.monotonic()
        results.extend(slow_results)

    total_time = time.monotonic() - start_time

    # Build comprehensive report
    report: dict[str, Any] = {
        "repo": str(repo_root),
        "detect": detect_info,
        "results": results,
        "timing": {
            "detect_ms": round((t_detect_end - t_detect_start) * 1000, 2),
            "fast_ms": round((t_fast_end - t_fast_start) * 1000, 2),
            "mutating_ms": round((t_mutating_end - t_mutating_start) * 1000, 2),
            "slow_ms": round((t_slow_end - t_slow_start) * 1000, 2),
            "total_ms": round(total_time * 1000, 2),
        },
        "profile": {
            "name": profile.name,
            "fast_count": len(fast_results),
            "mutating_count": len(mutating_results),
            "slow_count": len(slow_results),
        },
    }

    # 6) DEFER REPORT WRITE - don't block CLI
    # Note: The CLI will handle the durable reporting, so we skip it here
    # if report_path is not None:
    #     write_report_async(report_path, report, enabled=True)

    # existing code builds/collects results into `results`
    return _normalize_results_flat(results), report
