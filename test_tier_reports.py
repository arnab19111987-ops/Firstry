#!/usr/bin/env python3
"""
Test script for the new tier-aware reporting system.
"""
from __future__ import annotations
from firsttry.reports.summary import render_summary
from firsttry.reports.ui import render_run_progress  
from firsttry.reports.tier_map import TIER_CHECKS
from firsttry.license_guard import get_tier

def main():
    # Simulate orchestrator results
    mock_results = {
        "ruff": {
            "passed": True,
            "summary": "Code style looks good",
            "details": "Found 0 formatting issues in 45 files"
        },
        "mypy": {
            "passed": False, 
            "summary": "Type checking found 3 issues",
            "details": "mypy found 3 type errors:\n  src/main.py:42: error: Argument missing\n  tests/test_api.py:15: error: Invalid type"
        },
        "pytest": {
            "passed": True,
            "summary": "All tests passed",
            "details": "67 tests passed in 2.3s"
        },
        "bandit": {
            "passed": False,
            "summary": "Security scan found issues", 
            "details": "Found 2 potential security issues"
        },
        "pip-audit": {
            "passed": True,
            "summary": "No vulnerable dependencies",
            "details": "Scanned 45 packages, found 0 vulnerabilities"
        },
        "ci-parity": {
            "passed": True,
            "summary": "95% CI parity",
            "details": "Local setup matches 95% of CI environment"
        }
    }
    
    # Context information
    context = {
        "machine": "8",
        "files": 452,
        "tests": 67
    }
    
    # Show what tier we're running
    tier = (get_tier() or "free").lower()
    planned_checks = TIER_CHECKS.get(tier, TIER_CHECKS["free"])
    
    print(f"Running FirstTry in {tier} tier...")
    print(f"Planned checks: {', '.join(planned_checks)}")
    
    # Show progress simulation (just for UX)
    render_run_progress(planned_checks)
    
    # Show tier-aware summary with interactive menu
    render_summary(mock_results, context)

if __name__ == "__main__":
    main()