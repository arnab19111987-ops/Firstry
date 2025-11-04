from __future__ import annotations
from pathlib import Path
from .planner.dag import Plan
from .executor.dag import DagExecutor, default_caches

def run_plan(repo_root: Path, plan: Plan, use_remote_cache: bool, workers: int = 8):
    caches = default_caches(repo_root, use_remote_cache)
    ex = DagExecutor(repo_root=repo_root, plan=plan, caches=caches, max_workers=workers)
    results = ex.run()

    # TTY trust lines
    for tid, r in results.items():
        prefix = "[CACHE]" if r.status.startswith("hit-") else "[ RUN ]"
        print(f"{prefix} {r.status.upper():10s} {tid} ({r.duration_ms}ms)")
    print(f"\n{sum(1 for r in results.values() if r.status.startswith('hit-'))} checks verified from cache, {sum(1 for r in results.values() if not r.status.startswith('hit-'))} run locally.\n")
    return results
