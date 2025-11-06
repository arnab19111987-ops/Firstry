# src/firsttry/reports/detail.py
from __future__ import annotations

from typing import Any

from .ui import c


def render_detailed_report(results: dict[str, Any], allowed_checks: list[str]):
    print()
    print(c("📋 Detailed Report (your tier)", "bold"))
    print()
    for check_name, result in results.items():
        if check_name not in allowed_checks:
            continue
        print(c(f"▶ {check_name}", "cyan"))
        print(result.get("details", result.get("summary", "No additional info")))
        print(c("-" * 50, "blue"))
    print()


def render_locked_report(
    results: dict[str, Any],
    allowed_checks: list[str],
    locked_msg: str,
):
    print()
    print(c("🔒 Locked / Pro / Team Checks", "bold"))
    print()
    for check_name in results:
        if check_name in allowed_checks:
            continue
        print(c(f"▶ {check_name}", "yellow"))
        print(locked_msg)
        print(c("-" * 50, "blue"))
    print()
