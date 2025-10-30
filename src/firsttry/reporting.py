from __future__ import annotations

from typing import List

from .gates.base import GateResult


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
