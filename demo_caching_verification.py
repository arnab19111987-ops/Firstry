#!/usr/bin/env python3
"""Demo: Zero-run cache with all tasks passing.

Shows millisecond-level performance when repository state hasn't changed.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run_firsttry():
    """Run firsttry and capture timing."""
    start = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "firsttry.cli_dag", "run", "--report-json", ".firsttry/report.json"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    duration = time.time() - start
    return result, duration


def check_report():
    """Load and display report.json."""
    report_path = Path(__file__).parent.parent / ".firsttry" / "report.json"
    if not report_path.exists():
        print("No report.json found")
        return None

    report = json.loads(report_path.read_text())
    return report


def main():
    """Demonstrate caching system."""
    print("=" * 70)
    print("FirstTry Caching Demo")
    print("=" * 70)

    # Clean start
    cache_dir = Path(__file__).parent.parent / ".firsttry"
    if cache_dir.exists():
        import shutil

        shutil.rmtree(cache_dir)
    print("\n✓ Cleaned .firsttry cache\n")

    # Run 1: Cold (no cache)
    print("Run 1: Cold (no cache)")
    print("-" * 70)
    result1, dur1 = run_firsttry()
    report1 = check_report()
    print(f"Duration: {dur1:.3f}s")
    print(f"Exit code: {result1.returncode}")
    if report1:
        for task in report1.get("tasks", []):
            print(
                f"  {task['id']:8} code={task['code']} cache={task.get('cache', 'N/A'):4} dur={task.get('duration_s', 0):.3f}s"
            )
    print()

    # Run 2: Warm (task cache)
    print("Run 2: Warm (task cache)")
    print("-" * 70)
    result2, dur2 = run_firsttry()
    report2 = check_report()
    print(f"Duration: {dur2:.3f}s")
    print(f"Exit code: {result2.returncode}")
    if report2:
        cache_hits = sum(1 for t in report2.get("tasks", []) if t.get("cache") == "hit")
        print(f"Cache hits: {cache_hits}/{len(report2.get('tasks', []))}")
        for task in report2.get("tasks", []):
            print(
                f"  {task['id']:8} code={task['code']} cache={task.get('cache', 'N/A'):4} dur={task.get('duration_s', 0):.3f}s"
            )
    print()

    # Run 3: Zero-run (full cache if all passed)
    print("Run 3: Zero-run attempt (full cache if all tasks passed)")
    print("-" * 70)
    result3, dur3 = run_firsttry()
    report3 = check_report()
    print(f"Duration: {dur3:.3f}s")
    print(f"Exit code: {result3.returncode}")
    if report3:
        verified = report3.get("verified_from_cache", False)
        print(f"Verified from cache: {verified}")
        if verified:
            print("  ✓ Zero-run cache HIT - no tasks executed!")
            print(f"  ✓ Speedup: {dur1/dur3:.0f}x faster than cold run")
        else:
            cache_hits = sum(1 for t in report3.get("tasks", []) if t.get("cache") == "hit")
            print(f"  Cache hits: {cache_hits}/{len(report3.get('tasks', []))}")
            for task in report3.get("tasks", []):
                print(
                    f"    {task['id']:8} code={task['code']} cache={task.get('cache', 'N/A'):4} dur={task.get('duration_s', 0):.3f}s"
                )
            if result3.returncode != 0:
                print("  Note: Zero-run cache only triggers when all tasks pass (exit code 0)")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Cold run:     {dur1:.3f}s")
    print(f"Warm run:     {dur2:.3f}s ({(1 - dur2/dur1)*100:.0f}% faster)")
    print(f"Zero-run:     {dur3:.3f}s ({(1 - dur3/dur1)*100:.0f}% faster)")
    print()

    if report3 and report3.get("verified_from_cache"):
        print("✓ Zero-run cache HIT achieved!")
        print(f"✓ Performance: {dur3*1000:.1f}ms (target: <10ms)")
    else:
        print("✗ Zero-run cache MISS (some tasks failed or changed)")
        print("  To achieve zero-run cache hit:")
        print("  1. Ensure all tasks pass (exit code 0)")
        print("  2. Run again without changing any files")
        print("  3. Repo fingerprint will match and return cached report in ~1-5ms")


if __name__ == "__main__":
    main()
