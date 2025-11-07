"""DAG-based CLI orchestration for FirstTry (Task 6 integration)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from firsttry.runner.config import ConfigLoader
from firsttry.runner.executor import Executor
from firsttry.runner.model import DAG
from firsttry.runner.planner import Planner

# Optional: if you already have a summary reporter, import it; else we no-op.
try:
    from firsttry.reporting.summary import show_summary
except Exception:

    def show_summary(results: List[Dict[str, Any]]) -> None:  # minimal fallback
        ok = sum(1 for r in results if r.get("status") == "ok")
        fail = sum(1 for r in results if r.get("status") == "fail")
        print(f"[Summary] ok={ok} fail={fail} tasks={len(results)}")


def _ensure_report_dir(path: Path) -> None:
    """Create directory for report file if needed."""
    if path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_json_report(
    results: List[Dict[str, Any]], config: Dict[str, Any], out_path: Path
) -> None:
    """Write timestamped JSON report with task results and summary."""
    payload: Dict[str, Any] = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "config_used": bool(config),
        "tasks": results,
        "run_summary": {
            "total_tasks": len(results),
            "failed_tasks": sum(1 for r in results if r.get("status") == "fail"),
            "total_duration_ms": sum(int(r.get("duration_ms", 0)) for r in results),
        },
    }
    _ensure_report_dir(out_path)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[FirstTry] JSON report written → {out_path}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments for DAG-based CLI."""
    p = argparse.ArgumentParser(prog="firsttry", description="FirstTry DAG Orchestration CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Plan & execute the FirstTry DAG pipeline")
    run.add_argument(
        "--config-file",
        default="firsttry.toml",
        help="Path to config TOML (default: firsttry.toml)",
    )
    run.add_argument(
        "--report-json",
        default=".firsttry/report.json",
        help="Write JSON report to this path",
    )
    run.add_argument("--repo-root", default=".", help="Repository root (default: .)")
    run.add_argument("--quiet", action="store_true", help="Less chatter")
    run.add_argument("--dag-only", action="store_true", help="Plan only; print DAG and exit")

    return p.parse_args(argv)


def _build_dag_from_config(config_path: str, repo_root: str) -> DAG:
    """Load config and build DAG."""
    config_file = Path(config_path).resolve()
    repo_root_path = Path(repo_root).resolve()

    # Load config if file exists
    config: Dict[str, Any] = {}
    if config_file.exists():
        try:
            config = ConfigLoader.load(config_file)
        except Exception:
            config = {}

    # Build DAG using planner
    planner = Planner()
    workflow_config = config.get("workflow", {})
    dag = planner.build_dag(workflow_config, repo_root_path)

    return dag


def cmd_run(argv: list[str] | None = None) -> int:
    """Main DAG orchestration command."""
    args = _parse_args(argv)

    if args.cmd != "run":
        print(f"[FirstTry] Unknown command: {args.cmd}", file=sys.stderr)
        return 2

    # 1) Load config and build DAG
    if not args.quiet:
        print("[FirstTry] Loading configuration…")

    try:
        dag = _build_dag_from_config(args.config_file, args.repo_root)
    except Exception as e:
        print(f"[FirstTry] Error building DAG: {e}", file=sys.stderr)
        return 2

    if not args.quiet:
        print("[FirstTry] DAG planned successfully")

    # 2) Dry-run mode: print plan and exit
    if args.dag_only:
        print("\n--- DAG Plan (Dry Run) ---")
        print(f"Tasks: {list(dag.tasks.keys())}")
        print(f"Edges: {sorted(dag.edges)}")
        try:
            order = dag.toposort()
            print(f"Order: {order}")
        except ValueError as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    # 3) Execute DAG
    if not args.quiet:
        print(f"[FirstTry] Executing {len(dag.tasks)} tasks…")

    executor = Executor(dag, use_rust=None)
    exit_codes = executor.execute()

    # Convert exit codes to result dicts
    results: List[Dict[str, Any]] = []
    for task_id in dag.toposort():
        code = exit_codes.get(task_id, 1)
        results.append(
            {
                "id": task_id,
                "status": "ok" if code == 0 else "fail",
                "exit_code": code,
                "duration_ms": 0,  # Executor doesn't track duration currently
            }
        )

    # 4) Report
    if not args.quiet:
        print("[FirstTry] Generating summary…")

    show_summary(results)

    if args.report_json:
        config: Dict[str, Any] = {}
        try:
            config = ConfigLoader.load(args.config_file)
        except Exception:
            pass
        _write_json_report(results, config, Path(args.report_json))

    # 5) Exit status
    failed = [r for r in results if r.get("status") == "fail"]
    if failed:
        print(f"\n[FirstTry] FAILED: {len(failed)} task(s) failed.")
        return 1

    if not args.quiet:
        print("\n[FirstTry] SUCCESS: All checks passed.")
    return 0


def main(argv: list[str] | None = None) -> None:
    """Entry point for DAG CLI."""
    sys.exit(cmd_run(argv))


if __name__ == "__main__":
    main()
