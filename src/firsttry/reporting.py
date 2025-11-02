from __future__ import annotations

import sys
from typing import List, Dict, Any

# Import the GateResult from gates.base
from .gates.base import GateResult


def color(txt: str, code: str) -> str:
    if not sys.stdout.isatty():
        return txt
    return f"\033[{code}m{txt}\033[0m"


GREEN = "32"
RED = "31"
YELLOW = "33"


def print_report(report: dict):
    print("\n===== FirstTry Summary =====")
    if report["ok"]:
        print(color("✅ All checks passed", GREEN))
    else:
        print(color("❌ Some checks failed", RED))

    for step in report["summary"]:
        status = color("OK", GREEN) if step["ok"] else color("FAIL", RED)
        print(f"- {step['id']} ({step['lang']}): {status}")

        for r in step["results"]:
            if not r["ok"]:
                print(color(f"  • {r['cmd']}", YELLOW))
                if r["stderr"]:
                    print(f"    {r['stderr'].strip()[:200]}")

        if step["fixed"]:
            print(color(f"  • autofix applied ({len(step['fixed'])})", GREEN))


def print_summary(results: List[GateResult]) -> None:
    print("\n=== FirstTry Summary ===")
    ok_count = 0
    skip_count = 0
    fail_count = 0

    for r in results:
        if r.skipped:
            status = "[SKIP]"
            skip_count += 1
        elif r.ok:
            status = "[ OK ]"
            ok_count += 1
        else:
            status = "[FAIL]"
            fail_count += 1
        print(f"{status} {r.gate_id}")
        if r.reason and r.skipped:
            print(f"       reason: {r.reason}")
        if not r.ok and r.output:
            print("------- output -------")
            print(r.output.strip())
            print("----------------------")

    print(f"\nOK: {ok_count}  Skipped: {skip_count}  Failed: {fail_count}")


def normalize_cache_state(tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize cache state for honest reporting.
    
    tool_result {
      "name": ...,
      "status": "ok" | "fail" | "skipped",
      "cache_state": "hit" | "miss" | "re-run-failed" | None,
      ...
    }
    """
    cache_state = tool_result.get("cache_state")
    
    if cache_state == "re-run-failed":
        # count as structural hit - cache worked, we just re-ran due to policy
        tool_result["cache_bucket"] = "hit-policy"
    elif cache_state == "hit":
        tool_result["cache_bucket"] = "hit"
    else:
        tool_result["cache_bucket"] = "miss"
    
    return tool_result


def format_cache_summary(results: List[Dict[str, Any]]) -> str:
    """Format cache statistics with honest hit rate reporting."""
    normalized = [normalize_cache_state(r) for r in results]
    
    hits = len([r for r in normalized if r.get("cache_bucket") == "hit"])
    policy_reruns = len([r for r in normalized if r.get("cache_bucket") == "hit-policy"])
    misses = len([r for r in normalized if r.get("cache_bucket") == "miss"])
    
    total = hits + policy_reruns + misses
    if total == 0:
        return "Cache: No cached operations"
    
    structural_hits = hits + policy_reruns
    
    summary_parts: List[str] = []
    if structural_hits > 0:
        summary_parts.append(f"Cache (structural): {structural_hits}/{total}")
    if policy_reruns > 0:
        summary_parts.append(f"Cache (policy-respected): {policy_reruns} re-run (failed tools)")
    if misses > 0:
        summary_parts.append(f"Cache misses: {misses}")
    
    return "  ".join(summary_parts)


# Durable reporting for timing data and run results
import json
import os
from pathlib import Path
import asyncio

REPORT_DIR = Path(".firsttry")
REPORT_FILE = REPORT_DIR / "last_run.json"


def _ensure_dir() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def write_report_sync(payload: Dict[str, Any]) -> None:
    _ensure_dir()
    # write to tmp first, then move = atomic-ish
    tmp_path = REPORT_FILE.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(REPORT_FILE)


def write_report_sync_to_path(path: Path, payload: Dict[str, Any]) -> None:
    """Write report to specific path synchronously."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # write to tmp first, then move = atomic-ish
    tmp_path = path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(path)


async def write_report_async(path: Path, payload: Dict[str, Any], enabled: bool = True) -> None:
    """
    Fire-and-forget style, but still durable.
    If anything goes wrong in async context, fall back to sync.
    Compatible with old telemetry interface.
    """
    if not enabled:
        write_report_sync_to_path(path, payload)
        return
        
    try:
        loop = asyncio.get_running_loop()
        # run blocking write in thread so we don't block main
        await loop.run_in_executor(None, write_report_sync_to_path, path, payload)
    except RuntimeError:
        # no running loop / shutdown → just do sync
        write_report_sync_to_path(path, payload)
    except Exception:
        # last-resort guard
        write_report_sync_to_path(path, payload)
