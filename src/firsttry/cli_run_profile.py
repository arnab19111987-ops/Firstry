from __future__ import annotations

from pathlib import Path
import argparse
import asyncio
import json

from .lazy_orchestrator import run_profile_for_repo
from .reporting import write_report_async


def main():
    parser = argparse.ArgumentParser("firsttry run")
    parser.add_argument("--repo", default=".", help="Repo root")
    parser.add_argument(
        "--report",
        default=".firsttry/last_run.json",
        help="Where to write telemetry report",
    )
    parser.add_argument("--debug-report", action="store_true", help="Print report JSON before writing")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    report_path = repo_root / args.report

    # First get the raw results without writing the report
    results = run_profile_for_repo(repo_root, profile=None, report_path=None)
    
    # Now build the enhanced report with check-level timing data
    report_payload = {
        "repo": str(repo_root),
        "timing": {
            "total_ms": sum(r.get("duration_s", 0.0) * 1000 for r in results),
        },
        "checks": []
    }
    
    for result in results:
        duration_s = result.get("duration_s", result.get("elapsed", 0.0))
        last_duration_s = result.get("last_duration_s")
        
        check_data = {
            "name": result["name"],
            "status": "cached" if result.get("from_cache") else result["status"],
            "duration_s": duration_s,
        }
        if last_duration_s is not None:
            check_data["last_duration_s"] = last_duration_s
            
        report_payload["checks"].append(check_data)
    
    # Debug output if requested
    if args.debug_report:
        print("=== Report Payload ===")
        print(json.dumps(report_payload, indent=2))
        print("=====================")
    
    # Durable report writing with error handling
    try:
        # Check if we're already in an async context
        try:
            # Try to get the current running loop
            loop = asyncio.get_running_loop()
            # We're in an async context, create a background task
            loop.create_task(write_report_async(report_path, report_payload))
        except RuntimeError:
            # No running loop, create one for this operation
            asyncio.run(write_report_async(report_path, report_payload))
    except Exception as e:
        print(f"[firsttry] warning: failed to write timing report: {e}")
        print(json.dumps(report_payload.get("timing", {}), indent=2))
    
    # Print quick summary
    print(f"Ran {len(results)} tools")
    for result in results:
        status_emoji = "✅" if result["status"] == "ok" else "❌"
        cache_info = " (cached)" if result.get("from_cache") else ""
        
        # Show timing information
        duration = result.get("duration_s", result.get("elapsed", 0.0))
        last_duration = result.get("last_duration_s")
        timing_info = f" ({duration:.3f}s"
        if last_duration is not None and result.get("from_cache"):
            timing_info += f", was {last_duration:.1f}s"
        timing_info += ")"
        
        print(f"{status_emoji} {result['name']}{cache_info}{timing_info}")


if __name__ == "__main__":
    main()