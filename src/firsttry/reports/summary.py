# src/firsttry/reports/summary.py
from __future__ import annotations
from typing import Dict, Any
from .tier_map import TIER_CHECKS, LOCK_MESSAGE
from .ui import c, interactive_menu
from ..license_guard import get_tier  # your existing function
from .detail import render_detailed_report, render_locked_report


def render_summary(results: Dict[str, Any], context: Dict[str, Any]):
    tier = (get_tier() or "free").lower()
    allowed_checks = TIER_CHECKS.get(tier, TIER_CHECKS["free"])

    print()
    print(c(f"🔹 FirstTry ({tier.capitalize()}) — Local CI", "bold"))
    print()
    print(c("--- Context ---", "cyan"))
    print(f"  Machine: {context.get('machine', 'unknown')} CPUs")
    print(f"  Repo:    {context.get('files', '?')} files, {context.get('tests', '?')} tests")
    print("  Checks:  " + ", ".join(allowed_checks))
    print()

    print(c("--- Results ---", "cyan"))
    for check_name, result in results.items():
        if check_name in allowed_checks:
            passed = result.get("passed", False)
            details = result.get("summary", "No details")
            mark = c("✅", "green") if passed else c("❌", "red")
            print(f"  {mark} {c(check_name, 'bold')}: {details}")
        else:
            print(f"  {c(check_name, 'yellow')}: {LOCK_MESSAGE}")

    # overall
    print()
    print(c("--- Summary ---", "cyan"))
    passed_all = all(
        r.get("passed", True) for name, r in results.items() if name in allowed_checks
    )
    done_msg = c("✅ PASSED", "green") if passed_all else c("❌ FAILED", "red")
    print(f"  Result: {done_msg} ({len(allowed_checks)} checks run)")
    print()

    # attach interactive menu
    interactive_menu(
        results,
        allowed_checks,
        LOCK_MESSAGE,
        on_detail=render_detailed_report,
        on_locked=render_locked_report,
    )