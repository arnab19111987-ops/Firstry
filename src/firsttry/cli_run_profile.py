from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--debug-report",
        action="store_true",
        help="Print report JSON before writing",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    report_path = repo_root / args.report

    # First get the raw results without writing the report
    results, report = run_profile_for_repo(
        repo_root,
        profile=None,
        report_path=report_path,
    )

    # Build comprehensive report payload from orchestrator report with locked schema
    from datetime import datetime
    from datetime import timezone

    payload = {
        "schema_version": 1,
        "repo": report.get("repo", str(repo_root)),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "timing": report.get("timing", {"total_ms": 0.0}),
        "checks": [],
    }

    # Convert results to check format with timing info
    for result in results:
        status = "cached" if result.get("from_cache") else result.get("status", "unknown")
        duration = result.get("duration_s", result.get("elapsed", 0.0))
        last_duration = result.get("last_duration_s")

        check_data = {
            "name": result["name"],
            "status": status,
            "duration_s": duration,
        }
        if last_duration is not None:
            check_data["last_duration_s"] = last_duration

        payload["checks"].append(check_data)

    # Debug output if requested
    if args.debug_report:
        print("=== Report Payload ===")
        print(json.dumps(payload, indent=2))
        print("=====================")

    # Handle durable report writing with error handling and ensure we exit 0
    try:
        # Try to get running loop first
        try:
            loop = asyncio.get_running_loop()
            # background task, don't block
            loop.create_task(write_report_async(report_path, payload))
        except RuntimeError:
            # no running loop, create one and complete the write
            asyncio.run(write_report_async(report_path, payload))
        rc = 0
    except Exception as e:
        # Don't let report-writing failures make the CLI fail.
        print(f"[firsttry] warning: failed to write timing report: {e}")
        # Always show timing so CI/CD / humans can scrape it
        try:
            if "timing" in payload:
                print(json.dumps(payload["timing"], indent=2))
        except Exception:
            pass
        rc = 0

    # Print quick summary
    print(f"Ran {len(results)} tools")
    for result in results:
        status_emoji = "✅" if result.get("status") == "ok" else "❌"
        cache_info = " (cached)" if result.get("from_cache") else ""

        # Show timing information
        duration = result.get("duration_s", result.get("elapsed", 0.0))
        last_duration = result.get("last_duration_s")
        timing_info = f" ({duration:.3f}s"
        if last_duration is not None and result.get("from_cache"):
            timing_info += f", was {last_duration:.1f}s"
        timing_info += ")"

        print(f"{status_emoji} {result['name']}{cache_info}{timing_info}")

    sys.exit(rc)


if __name__ == "__main__":
    main()
