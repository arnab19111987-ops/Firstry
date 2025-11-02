#!/usr/bin/env python3
"""
Test the CLI integration with actual orchestrator results.
"""
from __future__ import annotations
from pathlib import Path
from firsttry.lazy_orchestrator import run_profile_for_repo
from firsttry.reports.cli_summary import render_cli_summary, convert_orchestrator_results_to_tier_format
from firsttry.reports.ui import render_run_progress
from firsttry.reports.tier_map import TIER_CHECKS
from firsttry.license_guard import get_tier

def main():
    repo_root = Path(".").resolve()
    
    # Show what tier we're running
    tier = (get_tier() or "free").lower()
    planned_checks = TIER_CHECKS.get(tier, TIER_CHECKS["free"])
    
    print(f"Running FirstTry in {tier} tier...")
    print(f"Planned checks: {', '.join(planned_checks)}")
    
    # Show progress simulation (just for UX)
    render_run_progress(planned_checks)
    
    # Run actual orchestrator
    results, report = run_profile_for_repo(repo_root, profile=None, report_path=None)
    
    # Convert to tier-aware format
    tier_results = convert_orchestrator_results_to_tier_format(results)
    
    # Build context from report
    context = {
        "machine": "8",  # Could get from system info
        "files": "452",  # Could get from repo scan
        "tests": "67"    # Could get from test discovery
    }
    
    # Render tier-aware summary (non-interactive for CLI)
    exit_code = render_cli_summary(tier_results, context, interactive=False)
    
    # Show timing breakdown if available
    if report and "timing" in report:
        timing = report["timing"]
        print(c("--- Performance ---", "cyan"))
        print(f"  Total: {timing.get('total_ms', 0):.1f}ms")
        print(f"  Phases: detect({timing.get('detect_ms', 0):.1f}ms) + fast({timing.get('fast_ms', 0):.1f}ms) + slow({timing.get('slow_ms', 0):.1f}ms)")
    
    return exit_code

if __name__ == "__main__":
    from firsttry.reports.ui import c
    exit(main())