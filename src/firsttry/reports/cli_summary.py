# src/firsttry/reports/cli_summary.py
"""
Non-interactive tier-aware summary for CLI integration.
"""
from __future__ import annotations
from typing import Dict, Any
from .tier_map import TIER_CHECKS, LOCKED_MESSAGE, get_checks_for_tier, get_tier_meta
from .ui import c
from ..license_guard import get_tier


def render_cli_summary(results: Dict[str, Any], context: Dict[str, Any], interactive: bool = False, tier: str | None = None) -> int:
    """
    Render tier-aware summary for CLI.
    Returns exit code: 0 for success, 1 for failure.
    """
    if tier is None:
        tier = get_tier() or "free-lite"
    allowed_checks = get_checks_for_tier(tier)

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
            print(f"  {c(check_name, 'yellow')}: {LOCKED_MESSAGE}")

    # overall
    print()
    print(c("--- Summary ---", "cyan"))
    passed_all = all(
        r.get("passed", True) for name, r in results.items() if name in allowed_checks
    )
    done_msg = c("✅ PASSED", "green") if passed_all else c("❌ FAILED", "red")
    print(f"  Result: {done_msg} ({len(allowed_checks)} checks run)")
    
    # Show upgrade hint for free tier
    if tier == "free" or tier == "developer":
        print()
        print(c("💡 Upgrade to FirstTry Pro to:", "yellow"))
        print("   • See full CI Parity (tools, env, deps, score)")
        print("   • Get plain-English fix suggestions for mypy/pytest/eslint")
        print("   • Enforce team-wide consistency via firsttry.toml")
    
    print()
    
    # Interactive menu only if requested  
    if interactive:
        from .summary import render_summary
        render_summary(results, context)
    
    return 0 if passed_all else 1


def convert_orchestrator_results_to_tier_format(orchestrator_results: list) -> Dict[str, Any]:
    """
    Convert orchestrator results to the format expected by tier-aware reporting.
    """
    results = {}
    
    for result in orchestrator_results:
        name = result.get("name", "unknown")
        status = result.get("status", "unknown")
        from_cache = result.get("from_cache", False)
        
        # Determine if passed
        passed = status == "ok"
        
        # Build summary message
        cache_info = " (cached)" if from_cache else ""
        duration = result.get("duration_s", result.get("elapsed", 0.0))
        timing_info = f" ({duration:.3f}s)" if duration > 0.001 else " (0.000s)"
        
        summary = f"{'Passed' if passed else 'Failed'}{cache_info}{timing_info}"
        
        # Get detailed info from meta if available
        meta = result.get("meta", {})
        details = meta.get("output", summary) if isinstance(meta, dict) else summary
        
        results[name] = {
            "passed": passed,
            "summary": summary,
            "details": details
        }
    
    return results