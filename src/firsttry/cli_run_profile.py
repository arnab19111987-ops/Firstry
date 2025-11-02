from __future__ import annotations

from pathlib import Path
import argparse

from .lazy_orchestrator import run_profile_for_repo


def main():
    parser = argparse.ArgumentParser("firsttry run")
    parser.add_argument("--repo", default=".", help="Repo root")
    parser.add_argument(
        "--report",
        default=".firsttry/last_run.json",
        help="Where to write telemetry report",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    report_path = repo_root / args.report

    results = run_profile_for_repo(repo_root, profile=None, report_path=report_path)
    
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