from __future__ import annotations

import argparse
import datetime as _dt
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from firsttry.reporting.jsonio import write_report
from firsttry.runner.config import load_graph_from_config
from firsttry.runner.executor import Executor
from firsttry.runner.planner import compute_levels
from firsttry.runner.planner import plan_levels_cached


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def main(argv=None):
    p = argparse.ArgumentParser("firsttry-dag")
    p.add_argument("run", nargs="?", default="run")
    p.add_argument("--config", default="firsttry.toml")
    p.add_argument("--report-json", default=".firsttry/report.json")
    p.add_argument("--no-capture-logs", action="store_true")
    p.add_argument("--max-workers", type=int, default=0)
    p.add_argument(
        "--prune-tests", action="store_true", help="Run only impacted pytest nodes when possible"
    )
    args = p.parse_args(argv)

    # Build the graph ONCE; pass a lambda that returns it only if cache miss.
    graph, prune_meta = load_graph_from_config(args.config, prune_tests=args.prune_tests)

    # If pruning is requested, compute levels directly from the pruned graph
    # to avoid serving a cached plan that doesn't include pruned nodeids.
    if args.prune_tests:
        lvls = compute_levels(graph)
    else:
        lvls = plan_levels_cached(args.config, lambda: graph)

    results = []
    level_stats = []
    executor = Executor(graph, use_external_logs=not args.no_capture_logs)
    # Ensure log dir exists when using external logs
    if executor.use_external_logs:
        os.makedirs(".firsttry/logs", exist_ok=True)

    for i, lvl in enumerate(lvls):
        maxw = args.max_workers or min(4, max(1, len(lvl)))
        with ThreadPoolExecutor(max_workers=maxw) as tp:
            futs = {tp.submit(executor._run_task, graph.tasks[tid]): tid for tid in lvl}
            completed = []
            for f in as_completed(futs):
                r = f.result()
                r["level"] = i  # Annotate which level executed
                completed.append(r)
                results.append(r)
        level_stats.append({"level": i, "size": len(lvl), "concurrency_used": maxw})

    report = {
        "run_timestamp": _now_iso(),
        "config_used": True,
        "levels": lvls,
        "level_stats": level_stats,  # Proof of parallelism
        "prune_metadata": prune_meta,  # Proof of pruning
        "tasks": results,
        "run_summary": {
            "total_tasks": len(results),
            "failed_tasks": sum(1 for r in results if r.get("code", 1) != 0),
            "total_duration_ms": 0,
        },
    }
    write_report(report, args.report_json)
    return 1 if any(r.get("code", 1) != 0 for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
