from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .cache import save_cache
from .gates.base import GateResult
from .runner_light import (
    GATE_REGISTRY,
    get_changed_files,
    get_profile,
    load_cache,
    should_skip_gate,
    update_gate_cache,
)

AUTOFIX_HINTS = {
    "python:ruff": "ruff fix .",
    "precommit:all": "pre-commit run --all-files",
    # later: "python:black:check": "black .",
}


def _is_strict(name: str) -> bool:
    return name == "strict"


def run_pipeline(profile: str, since: str | None) -> list[GateResult]:
    root = Path()
    prof = get_profile(profile)
    strict_mode = _is_strict(prof.name)

    if strict_mode:
        cache = {}
        changed: list[str] = []
    else:
        cache = load_cache(root)
        changed = get_changed_files(root, since)

    results: list[GateResult] = []
    to_run: list[str] = []

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
                ),
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
                    ),
                )
                continue

            if since and should_skip_gate(cache, gate_id, changed):
                results.append(
                    GateResult(
                        gate_id=gate_id,
                        ok=True,
                        skipped=True,
                        reason="cached and unchanged",
                    ),
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


def build_issue_report(results: list[GateResult]) -> dict[str, Any]:
    total = len(results)
    failed = [r for r in results if not r.ok and not r.skipped]
    skipped = [r for r in results if r.skipped]
    passed = [r for r in results if r.ok and not r.skipped]

    per_gate: dict[str, Any] = {}
    for r in results:
        per_gate[r.gate_id] = {
            "ok": r.ok,
            "skipped": r.skipped,
            "reason": r.reason or "",
            "output": r.output or "",
            "autofix": AUTOFIX_HINTS.get(r.gate_id),
        }

    by_type: dict[str, list[str]] = {
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


def print_human_report(report: dict[str, Any], show_details: bool = False) -> None:
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


def _is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _interactive_menu(report: dict[str, Any]) -> int:
    failed = [g for g, info in report["per_gate"].items() if not info["ok"] and not info["skipped"]]
    if not failed:
        print("\n✅ Nothing to fix. You’re good.")
        return 0

    print("\nWhat do you want to do next?")
    print("[1] Show detailed report with gate outputs")
    print("[2] Let FirstTry attempt safe fixes for autofixable issues")
    print("[3] Cancel (I will fix manually)")

    try:
        choice = input("Choose 1 / 2 / 3: ").strip()
    except EOFError:
        # non-interactive shell — just print summary and exit 1
        print("\n(non-interactive shell, skipping interactive choices)")
        return 1

    if choice == "1":
        print_human_report(report, show_details=True)
        return 1  # still fail, because issues exist

    if choice == "2":
        _run_safe_fixes(report)
        # after fixes we still exit 1 to let user re-run
        return 1

    # choice == "3" or anything else
    return 1


SAFE_AUTOFIX_CMDS = {
    "python:ruff": ["ruff", "check", "--fix", "."],
    "precommit:all": ["pre-commit", "run", "--all-files"],
    # later: "python:black:check": ["black", "."],
}


def _run_safe_fixes(report: dict[str, Any]) -> None:
    print("\n🛠  Running safe fixes...")
    for gate_id, info in report["per_gate"].items():
        if info["ok"] or info["skipped"]:
            continue
        cmd = SAFE_AUTOFIX_CMDS.get(gate_id)
        if not cmd:
            continue
        print(f"→ {gate_id}: {' '.join(cmd)}")
        try:
            import subprocess

            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            print("   (skipped: tool not installed)")
    print("Done. Re-run `firsttry ... report` to verify.")


def main() -> int:
    parser = argparse.ArgumentParser("firsttry")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="run gates for a profile")
    run_p.add_argument(
        "--profile",
        default="fast",
        choices=["fast", "strict", "release"],
    )
    run_p.add_argument("--since", default=None)

    rep_p = sub.add_parser("report", help="run and show detailed report")
    rep_p.add_argument(
        "--profile",
        default="strict",
        choices=["fast", "strict", "release"],
    )
    rep_p.add_argument("--since", default=None)
    rep_p.add_argument("--detail", action="store_true")
    rep_p.add_argument("--json", action="store_true")
    rep_p.add_argument(
        "--interactive",
        action="store_true",
        help="ask what to do next (local use only)",
    )

    args = parser.parse_args()

    if args.cmd == "run":
        results = run_pipeline(args.profile, args.since)
        failed = any((not r.ok and not r.skipped) for r in results)
        return 1 if failed else 0

    if args.cmd == "report":
        results = run_pipeline(args.profile, args.since)
        report = build_issue_report(results)

        # JSON mode → never interactive
        if args.json:
            print(json.dumps(report, indent=2))
            return 1 if report["failed"] else 0

        # normal human report
        print_human_report(report, show_details=args.detail)

        # interactive (only if TTY)
        if args.interactive and _is_tty():
            return _interactive_menu(report)

        return 1 if report["failed"] else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
