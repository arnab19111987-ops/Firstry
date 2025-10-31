from __future__ import annotations

import sys
from typing import List

# Import the GateResult from gates.base
from .gates.base import GateResult


def color(txt: str, code: str) -> str:
    if not sys.stdout.isatty():
        return txt
    return f"\033[{code}m{txt}\033[0m"


GREEN = "32"
RED = "31"
YELLOW = "33"


def print_report(report: dict):
    print("\n===== FirstTry Summary =====")
    if report["ok"]:
        print(color("✅ All checks passed", GREEN))
    else:
        print(color("❌ Some checks failed", RED))

    for step in report["summary"]:
        status = color("OK", GREEN) if step["ok"] else color("FAIL", RED)
        print(f"- {step['id']} ({step['lang']}): {status}")

        for r in step["results"]:
            if not r["ok"]:
                print(color(f"  • {r['cmd']}", YELLOW))
                if r["stderr"]:
                    print(f"    {r['stderr'].strip()[:200]}")

        if step["fixed"]:
            print(color(f"  • autofix applied ({len(step['fixed'])})", GREEN))


def print_summary(results: List[GateResult]) -> None:
    print("\n=== FirstTry Summary ===")
    ok_count = 0
    skip_count = 0
    fail_count = 0

    for r in results:
        if r.skipped:
            status = "[SKIP]"
            skip_count += 1
        elif r.ok:
            status = "[ OK ]"
            ok_count += 1
        else:
            status = "[FAIL]"
            fail_count += 1
        print(f"{status} {r.gate_id}")
        if r.reason and r.skipped:
            print(f"       reason: {r.reason}")
        if not r.ok and r.output:
            print("------- output -------")
            print(r.output.strip())
            print("----------------------")

    print(f"\nOK: {ok_count}  Skipped: {skip_count}  Failed: {fail_count}")
