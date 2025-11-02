# src/firsttry/reports/summary.py

from __future__ import annotations

from .tier_map import (
    get_checks_for_tier,
    get_tier_meta,
    LOCKED_MESSAGE,
    TIER_CHECKS,
)
from ..license_guard import get_tier

# you probably already have a Rich detection; keep it
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    _HAS_RICH = True
except Exception:
    _HAS_RICH = False
    console = None


def render_summary(report: dict) -> None:
    """
    `report` is whatever your orchestrator produced:
    {
        "results": {
            "ruff": {...},
            "mypy": {...},
            ...
        },
        ...
    }
    """
    tier = get_tier()
    meta = get_tier_meta(tier)
    allowed_checks = set(get_checks_for_tier(tier))

    title = meta["title"]
    subtitle = meta["subtitle"]

    if _HAS_RICH:
        console.rule(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[dim]{subtitle}[/dim]\n")

        table = Table(title="Summary (tier-aware)")
        table.add_column("Check", style="bold")
        table.add_column("Status")
        table.add_column("Details")

        all_checks_in_report = list(report.get("results", {}).keys())

        # Always show in THIS order: whatever is in TIER_CHECKS master order
        master_order = []
        for t, checks in TIER_CHECKS.items():
            for chk in checks:
                if chk not in master_order:
                    master_order.append(chk)
        # plus anything else that was actually run
        for chk in all_checks_in_report:
            if chk not in master_order:
                master_order.append(chk)

        for chk in master_order:
            res = report.get("results", {}).get(chk)
            if chk in allowed_checks:
                status = res.get("status", "unknown") if res else "unknown"
                emoji = "✅" if status == "ok" else "❌"
                table.add_row(chk, emoji, res.get("message", "") if res else "")
            else:
                # locked
                table.add_row(chk, "🔒", LOCKED_MESSAGE)

        console.print(table)
    else:
        # fallback
        print(f"{title}")
        print(f"{subtitle}")
        print()
        all_checks_in_report = list(report.get("results", {}).keys())
        for chk in all_checks_in_report:
            if chk in allowed_checks:
                res = report["results"].get(chk, {})
                status = res.get("status", "unknown")
                emoji = "✅" if status == "ok" else "❌"
                print(f"  {emoji} {chk}: {res.get('message','')}")
            else:
                print(f"  🔒 {chk}: {LOCKED_MESSAGE}")


# Legacy function for backward compatibility  
def render_summary_legacy(results, context):
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