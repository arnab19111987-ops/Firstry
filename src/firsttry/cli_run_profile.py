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
        print(f"{status_emoji} {result['name']}{cache_info}")


if __name__ == "__main__":
    main()