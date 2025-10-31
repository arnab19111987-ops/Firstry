# firsttry/orchestrator.py
from pathlib import Path
from .licensing import ensure_license_interactive
from .planner import build_plan  # new/pipeline engine
from .executor import execute_plan  # old/stable engine
from .reporting import print_report  # enhanced reporting
from .setup_wizard import run_setup as wizard_run
from .detectors import detect_languages
from .gates import core_checks as g

LAST_REPORT: dict | None = None  # simple in-memory; later can write to ~/.firsttry


def _maybe_license(no_prompt: bool):
    if no_prompt:
        return
    try:
        ensure_license_interactive()
    except SystemExit:
        print("Skipping license check for demo...")


def print_ci_like_conclusion(report: dict):
    """Print a final CI-like conclusion."""
    if report["ok"]:
        print("\n🎉 All checks passed! Ready to commit & push.")
    else:
        failed_count = len([s for s in report["summary"] if not s["ok"]])
        total_count = len(report["summary"])
        print(f"\n❌ {failed_count}/{total_count} checks failed.")

        # Show autofix suggestion if applicable
        fixable_steps = [s for s in report["summary"] if not s["ok"] and s.get("fixed")]
        autofix_available = any(
            s
            for s in report["summary"]
            if not s["ok"]
            and any(step.get("autofix", []) for step in [s] if "autofix" in s)
        )

        if autofix_available:
            print("💡 Try: firsttry fix")
        else:
            print("💡 Manual fixes required for some checks.")


def run_unified(gates_or_root=".", autofix=False, no_license_prompt=False, profile=None):
    """Main unified run command - supports both list of gates and legacy interface."""
    
    # Check if first argument is a list of gates (new interface)
    if isinstance(gates_or_root, list):
        return run_unified_gates(gates_or_root)
    
    # Legacy interface - first arg is root path
    root = gates_or_root
    if profile is None:
        profile = "fast"  # default to fast for speed

    _maybe_license(no_prompt=no_license_prompt)

    # 1) PLAN (pipeline engine - fast language detection)
    plan = build_plan(root=root)

    if not plan["steps"]:
        print("🤷 No checks to run (no supported languages detected)")
        return 0

    print(f"🔍 Detected: {', '.join(plan['languages'])}")

    # 2) EXECUTE with tiered approach
    if profile == "fast":
        # "fast but useful": run only tier 1 (≤5s)
        print("🚀 Running fast checks (tier 1)...")
        report = execute_plan(
            plan, max_tier=1, autofix=autofix, interactive_autofix=not autofix
        )
    elif profile == "strict":
        # "full / strict": run all tiers
        print("🚀 Running all checks (full validation)...")
        # First run tier 1
        report = execute_plan(
            plan, max_tier=1, autofix=autofix, interactive_autofix=not autofix
        )
        if report["ok"]:
            print("⏱  Fast checks passed. Running slower checks now...", flush=True)
            # Then run tier 2
            report = execute_plan(
                plan, max_tier=None, autofix=autofix, interactive_autofix=not autofix
            )
        else:
            print("❌ Fast checks failed. Skipping slower checks.")
    else:
        # unknown profile → be nice, default to fast
        print(f"🚀 Running fast checks (tier 1, unknown profile '{profile}')...")
        report = execute_plan(
            plan, max_tier=1, autofix=autofix, interactive_autofix=not autofix
        )

    # 3) REPORT (enhanced/pretty output)
    print_report(report)
    print_ci_like_conclusion(report)

    # Store for status command
    global LAST_REPORT
    LAST_REPORT = report

    return 0 if report["ok"] else 1


GATE_MAP = {
    # Level 1
    "lint_basic": g.run_lint_basic,
    "autofix": g.run_autofix,
    "repo_sanity": g.run_repo_sanity,

    # Level 2
    "type_check_fast": g.run_type_check_fast,
    "tests_fast": g.run_tests_fast,
    "env_deps_check": g.run_env_deps_check,

    # Level 3
    "duplication_fast": g.run_duplication_fast,
    "security_light": g.run_security_light,
    "coverage_warn": g.run_coverage_warn,
    "conventions": g.run_conventions,

    # Level 4
    "type_check_strict": g.run_type_check_strict,
    "tests_full": g.run_tests_full,
    "duplication_full": g.run_duplication_full,
    "security_full": g.run_security_full,
    "coverage_enforce": g.run_coverage_enforce,
    "migrations_drift": g.run_migrations_drift,
    "deps_license": g.run_deps_license,
}


def run_unified_gates(gates: list[str]) -> bool:
    """Run each gate sequentially."""
    all_ok = True
    for gate in gates:
        func = GATE_MAP.get(gate)
        print(f"→ Running {gate}")
        if func is None:
            print(f"   ⚠️  Gate {gate} not found.")
            continue
        try:
            ok = func()
            if not ok:
                all_ok = False
        except Exception as e:
            print(f"   ⚠️  {gate} crashed: {e}")
            all_ok = False
    return all_ok


def run_fix_only(root=".", no_license_prompt=False):
    """Run only autofix-capable steps."""
    _maybe_license(no_prompt=no_license_prompt)

    # 1) PLAN
    plan = build_plan(root=root)

    # 2) Filter to only autofix-capable steps
    fixable_steps = [s for s in plan["steps"] if s.get("autofix")]

    if not fixable_steps:
        print("🤷 No autofix-capable checks found")
        return 0

    plan["steps"] = fixable_steps

    print(f"🔧 Running autofix for {len(fixable_steps)} checks...")

    # 3) EXECUTE with autofix enabled, no interaction
    report = execute_plan(plan, autofix=True, interactive_autofix=False)

    # 4) REPORT
    print_report(report)
    print_ci_like_conclusion(report)

    global LAST_REPORT
    LAST_REPORT = report

    return 0 if report["ok"] else 1


def run_setup():
    """Interactive setup."""
    wizard_run()
    return 0


def show_status():
    """Show current status: detected languages, last run, missing tools."""
    cwd = Path.cwd()
    root_langs = detect_languages(cwd)

    print("FirstTry Status")
    print("=" * 20)
    print(f"📁 Project root: {cwd}")
    print(
        f"🔎 Detected languages: {', '.join(sorted(root_langs)) if root_langs else 'none'}"
    )

    # Show git status
    git_dir = cwd / ".git"
    if git_dir.exists():
        print("📋 Git repository: ✅")
        hooks_dir = git_dir / "hooks"
        pre_commit = hooks_dir / "pre-commit"
        if pre_commit.exists():
            print("🪝 Git hooks: ✅ installed")
        else:
            print("🪝 Git hooks: ❌ not installed (run 'firsttry setup')")
    else:
        print("📋 Git repository: ❌ not found")

    # Show last run
    if LAST_REPORT:
        status = "✅ PASSED" if LAST_REPORT["ok"] else "❌ FAILED"
        step_count = len(LAST_REPORT["summary"])
        print(f"📊 Last run: {status} ({step_count} checks)")
    else:
        print("📊 Last run: none in this session")

    # Show potential plan
    if root_langs:
        plan = build_plan(str(cwd))
        step_count = len(plan["steps"])
        print(f"🎯 Available checks: {step_count} steps")

        # Show missing tools (simplified)
        print("\n💡 Next steps:")
        if not LAST_REPORT:
            print("  • Run 'firsttry run' to check your code")
        elif not LAST_REPORT["ok"]:
            print("  • Run 'firsttry fix' to apply automatic fixes")
            print("  • Run 'firsttry run' to re-check")
        else:
            print("  • All good! Make your commit.")

    return 0
