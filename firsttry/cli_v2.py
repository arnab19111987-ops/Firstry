from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

from .runner_light import (
    get_profile,
    load_cache,
    get_changed_files,
    should_skip_gate,
    update_gate_cache,
    GATE_REGISTRY,
)
from .cache import save_cache
from .gates.base import GateResult

AUTOFIX_HINTS = {
    "python:ruff": "ruff fix .",
    "precommit:all": "pre-commit run --all-files",
    # later: "python:black:check": "black .",
}


def _is_strict(name: str) -> bool:
    return name == "strict"


def run_pipeline(profile: str, since: str | None) -> List[GateResult]:
    root = Path(".")
    prof = get_profile(profile)
    strict_mode = _is_strict(prof.name)

    if strict_mode:
        cache = {}
        changed: list[str] = []
    else:
        cache = load_cache(root)
        changed = get_changed_files(root, since)

    results: List[GateResult] = []
    to_run: List[str] = []

    # pick gates
    for gate_ref in prof.gates:
        optional = gate_ref.endswith("?")
        gate_id = gate_ref.rstrip("?")
        gate_cls = GATE_REGISTRY.get(gate_id)
        if not gate_cls:
            results.append(
                GateResult(
                    gate_id=gate_id,
                    ok=optional,
                    skipped=optional,
                    reason="gate not registered",
                )
            )
            continue

        gate = gate_cls()

        if not strict_mode:
            # adaptive
            if since and not gate.should_run_for(changed):
                results.append(
                    GateResult(
                        gate_id=gate_id,
                        ok=True,
                        skipped=True,
                        reason="not impacted by changes",
                    )
                )
                continue

            if since and should_skip_gate(cache, gate_id, changed):
                results.append(
                    GateResult(
                        gate_id=gate_id,
                        ok=True,
                        skipped=True,
                        reason="cached and unchanged",
                    )
                )
                continue

        to_run.append(gate_id)

    # run in parallel
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {}
        for gate_id in to_run:
            gate = GATE_REGISTRY[gate_id]()
            fut = ex.submit(gate.run, root)
            fut_map[fut] = gate_id
        for fut in as_completed(fut_map):
            res: GateResult = fut.result()
            results.append(res)
            if (not strict_mode) and res.ok and res.watched_files:
                update_gate_cache(cache, res.gate_id, res.watched_files)

    if not strict_mode:
        save_cache(root, cache)

    return results


def build_issue_report(results: List[GateResult]) -> Dict[str, Any]:
    total = len(results)
    failed = [r for r in results if not r.ok and not r.skipped]
    skipped = [r for r in results if r.skipped]
    passed = [r for r in results if r.ok and not r.skipped]

    per_gate: Dict[str, Any] = {}
    for r in results:
        per_gate[r.gate_id] = {
            "ok": r.ok,
            "skipped": r.skipped,
            "reason": r.reason or "",
            "output": r.output or "",
            "autofix": AUTOFIX_HINTS.get(r.gate_id),
        }

    by_type: Dict[str, list[str]] = {
        "lint": [],
        "typing": [],
        "tests": [],
        "security": [],
        "config": [],
        "deps": [],
        "env": [],
        "ci": [],
        "other": [],
    }
    for r in failed:
        gid = r.gate_id
        if gid.startswith("python:ruff") or gid.startswith("python:black"):
            by_type["lint"].append(gid)
        elif gid.startswith("python:mypy"):
            by_type["typing"].append(gid)
        elif gid.startswith("python:pytest") or gid.startswith("coverage:"):
            by_type["tests"].append(gid)
        elif gid.startswith("security:"):
            by_type["security"].append(gid)
        elif gid.startswith("config:"):
            by_type["config"].append(gid)
        elif gid.startswith("deps:"):
            by_type["deps"].append(gid)
        elif gid.startswith("env:"):
            by_type["env"].append(gid)
        elif gid.startswith("ci:"):
            by_type["ci"].append(gid)
        else:
            by_type["other"].append(gid)

    return {
        "total": total,
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "per_gate": per_gate,
        "by_type": by_type,
    }


def print_human_report(report: Dict[str, Any], show_details: bool = False) -> None:
    print("╔════════════════════════════════╗")
    print("║     FirstTry — Local CI        ║")
    print("╚════════════════════════════════╝")

    print(f"Total gates: {report['total']}")
    print(f"Passed:      {report['passed']}")
    print(f"Failed:      {report['failed']}")
    print(f"Skipped:     {report['skipped']}")

    if report["failed"]:
        print("\n❌ Issues by category:")
        for cat, items in report["by_type"].items():
            if items:
                print(f"  - {cat}: {len(items)} ({', '.join(items)})")
    else:
        print("\n✅ No failing gates.")

    autofix_lines = []
    for gate_id, info in report["per_gate"].items():
        if info["autofix"] and info["ok"] is False and info["skipped"] is False:
            autofix_lines.append((gate_id, info["autofix"]))

    if autofix_lines:
        print("\n🛠  Autofix suggestions:")
        for gate_id, cmd in autofix_lines:
            print(f"  - {gate_id}: run `{cmd}`")

    if show_details:
        print("\n📄 Details:")
        for gate_id, info in report["per_gate"].items():
            if info["skipped"]:
                continue
            if not info["output"] and not info["reason"]:
                continue
            print(f"\n--- {gate_id} ---")
            if info["reason"]:
                print(f"reason: {info['reason']}")
            if info["output"]:
                print(info["output"].strip())


def main() -> int:
    parser = argparse.ArgumentParser("firsttry")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="run gates for a profile")
    run_p.add_argument("--profile", default="fast", choices=["fast", "strict", "release"])
    run_p.add_argument("--since", default=None)

    rep_p = sub.add_parser("report", help="run and show detailed report")
    rep_p.add_argument("--profile", default="strict", choices=["fast", "strict", "release"])
    rep_p.add_argument("--since", default=None)
    rep_p.add_argument("--detail", action="store_true")
    rep_p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.cmd == "run":
        results = run_pipeline(args.profile, args.since)
        failed = any((not r.ok and not r.skipped) for r in results)
        return 1 if failed else 0

    if args.cmd == "report":
        results = run_pipeline(args.profile, args.since)
        report = build_issue_report(results)
        if args.json:
            print(json.dumps(report, indent=2))
            return 1 if report["failed"] else 0
        print_human_report(report, show_details=args.detail)
        return 1 if report["failed"] else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
