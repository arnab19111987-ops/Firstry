# CLI Integration Guide for Tier-Aware Reporting

## To integrate the new tier-aware reporting system into src/firsttry/cli.py:

### 1. Replace the existing summary section

**Current code (around line 447):**
```python
# Use SummaryPrinter for output
from .summary import print_run_summary

# Map tiers: developer->free, teams->pro, enterprise->pro
display_tier = "free" if tier == "developer" else "pro"
return print_run_summary(summary_results, meta, display_tier)
```

**Replace with:**
```python
# Use new tier-aware reporting
from .reports.cli_summary import render_cli_summary, convert_orchestrator_results_to_tier_format
from .reports.ui import render_run_progress
from .reports.tier_map import TIER_CHECKS

# Show progress before running checks (optional UX enhancement)
tier_name = tier.lower()
planned_checks = TIER_CHECKS.get(tier_name, TIER_CHECKS["free"])
render_run_progress(planned_checks)

# Convert orchestrator results to tier format
# Note: You'll need to get actual orchestrator results instead of summary_results
# Replace this section with call to lazy_orchestrator
tier_results = convert_orchestrator_results_to_tier_format(orchestrator_results)

# Build context from repo_profile and system info
context = {
    "machine": ctx.get("cpus", "unknown"),
    "files": repo_profile.get("total_files", "?"), 
    "tests": repo_profile.get("test_files", "?")
}

# Render tier-aware summary and return exit code
return render_cli_summary(tier_results, context, interactive=False)
```

### 2. If you want to use the lazy orchestrator instead of the current system:

**Replace the orchestrator call section:**
```python
# Current:
result = await run_checks_with_allocation_and_plan(...)

# Replace with:
from .lazy_orchestrator import run_profile_for_repo
results, report = run_profile_for_repo(
    repo_root=Path(ctx["repo_root"]),
    profile=None,  # or build from plan
    report_path=None  # or specify report location
)
```

### 3. Add optional --interactive flag for the full menu experience:

**In argument parser:**
```python
parser.add_argument("--interactive", action="store_true", 
                    help="Show interactive menu after summary")
```

**In CLI logic:**
```python
interactive = getattr(args, "interactive", False)
return render_cli_summary(tier_results, context, interactive=interactive)
```

### 4. Example of complete integration:

```python
async def run_fast_pipeline(*, args=None) -> int:
    # ... existing setup code ...
    
    # Get tier and planned checks
    tier = get_tier() or "developer"
    tier_name = tier.lower()
    planned_checks = TIER_CHECKS.get(tier_name, TIER_CHECKS["free"])
    
    # Show progress (optional)
    render_run_progress(planned_checks)
    
    # Run lazy orchestrator
    repo_root = Path(ctx["repo_root"])
    results, report = run_profile_for_repo(repo_root, profile=None, report_path=None)
    
    # Convert to tier format
    tier_results = convert_orchestrator_results_to_tier_format(results)
    
    # Build context
    context = {
        "machine": ctx.get("cpus", "unknown"),
        "files": repo_profile.get("total_files", "?"),
        "tests": repo_profile.get("test_files", "?")
    }
    
    # Render and return
    interactive = getattr(args, "interactive", False)
    return render_cli_summary(tier_results, context, interactive=interactive)
```

This gives you:
- Clean tier-aware output with only unlocked checks visible
- Locked check hints with upgrade messaging
- Optional interactive menu for detailed reports
- Performance timing visibility 
- Proper exit codes based on check results
- Rich progress bars when available, ANSI fallback otherwise