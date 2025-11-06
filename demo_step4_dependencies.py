#!/usr/bin/env python3
"""
Demo for Step 4: Conditional Check Dependencies

Shows how FirstTry intelligently skips expensive checks when prerequisites fail,
implementing fail-fast logic to save significant execution time.
"""

import asyncio
import tempfile
from pathlib import Path

# Import FirstTry modules
import sys

sys.path.insert(0, "/workspaces/Firstry/src")

from firsttry.check_dependencies import (
    DEPENDENCY_RULES,
    get_dependency_graph,
    should_skip_due_to_dependencies,
    analyze_dependency_impact,
    get_execution_order,
    get_dependency_insights,
    validate_dependency_rules,
)
from firsttry.cached_orchestrator import run_checks_for_profile


def demo_dependency_rules():
    """Demo the dependency rules configuration"""
    print("🎯 Step 4: Conditional Check Dependencies")
    print("=" * 50)

    print("📋 Dependency Rules Configuration:")
    for i, rule in enumerate(DEPENDENCY_RULES, 1):
        strictness = "STRICT" if rule.strict else "flexible"
        print(f"  {i}. {rule.dependent} ← {rule.prerequisite} ({strictness})")
        print(f"     Reason: {rule.reason}")

    print("\n📊 Rules Summary:")
    print(f"   • Total Rules: {len(DEPENDENCY_RULES)}")
    print(f"   • Strict Rules: {len([r for r in DEPENDENCY_RULES if r.strict])}")
    print(f"   • Flexible Rules: {len([r for r in DEPENDENCY_RULES if not r.strict])}")


def demo_dependency_graph():
    """Demo dependency graph visualization"""
    print("\n🕸️ Dependency Graph Analysis")
    print("-" * 40)

    graph = get_dependency_graph()

    print("📊 Dependency Graph:")
    for dependent, prerequisites in graph.items():
        print(f"  {dependent} depends on: {', '.join(prerequisites)}")

    # Show most critical prerequisites
    prerequisite_counts = {}
    for rule in DEPENDENCY_RULES:
        prereq = rule.prerequisite
        prerequisite_counts[prereq] = prerequisite_counts.get(prereq, 0) + 1

    if prerequisite_counts:
        most_critical = max(prerequisite_counts.items(), key=lambda x: x[1])
        print("\n🎯 Most Critical Prerequisite:")
        print(f"   '{most_critical[0]}' blocks {most_critical[1]} other checks")


def demo_execution_order():
    """Demo optimal execution order calculation"""
    print("\n⚡ Execution Order Optimization")
    print("-" * 40)

    all_checks = ["ruff", "black", "mypy", "pytest", "npm test", "ci-parity"]
    execution_levels = get_execution_order(all_checks)

    print("📋 Optimal Execution Order:")
    for level, checks in enumerate(execution_levels):
        parallelism = "parallel" if len(checks) > 1 else "serial"
        print(f"  Level {level}: {', '.join(checks)} ({parallelism})")

    print("\n💡 Benefits:")
    print("   • Prerequisites run first automatically")
    print("   • Independent checks can run in parallel")
    print("   • Failed prerequisites block dependent checks")


def demo_skip_logic():
    """Demo skip logic with different scenarios"""
    print("\n🚫 Skip Logic Scenarios")
    print("-" * 40)

    scenarios = [
        {"name": "No failures", "failed_checks": set(), "profile": "dev"},
        {
            "name": "Ruff fails (dev profile)",
            "failed_checks": {"ruff"},
            "profile": "dev",
        },
        {
            "name": "Ruff fails (strict profile)",
            "failed_checks": {"ruff"},
            "profile": "strict",
        },
        {"name": "Black fails", "failed_checks": {"black"}, "profile": "dev"},
    ]

    all_checks = ["ruff", "black", "mypy", "pytest", "npm test", "ci-parity"]

    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        skipped_checks = []

        for check in all_checks:
            blocking_rule = should_skip_due_to_dependencies(
                check, scenario["failed_checks"], scenario["profile"]
            )
            if blocking_rule:
                skipped_checks.append(
                    {
                        "check": check,
                        "blocked_by": blocking_rule.prerequisite,
                        "reason": blocking_rule.reason,
                        "strict": blocking_rule.strict,
                    }
                )

        if skipped_checks:
            print(f"   Skipped checks: {len(skipped_checks)}")
            for skip in skipped_checks:
                strictness = " (STRICT)" if skip["strict"] else ""
                print(f"     ❌ {skip['check']} ← blocked by {skip['blocked_by']}{strictness}")
        else:
            print("   ✅ All checks would run")


def demo_impact_analysis():
    """Demo performance impact analysis"""
    print("\n📈 Performance Impact Analysis")
    print("-" * 40)

    all_checks = ["ruff", "black", "mypy", "pytest", "npm test", "ci-parity"]

    # Scenario: ruff fails (common case)
    failed_checks = {"ruff"}

    for profile in ["dev", "strict"]:
        analysis = analyze_dependency_impact(all_checks, failed_checks, profile)

        print(f"\n📊 Profile: {profile}")
        print(f"   • Total checks: {analysis['total_checks']}")
        print(f"   • Skipped checks: {analysis['skipped_checks']}")
        print(f"   • Efficiency gain: {analysis['efficiency_gain']}")

        if analysis["skipped_details"]:
            print("   • Skipped details:")
            for check, details in analysis["skipped_details"].items():
                print(f"     - {check}: {details['reason']}")

    # Calculate time savings (estimated)
    print("\n⏱️ Time Savings Estimation:")
    print("   • Ruff failure scenario:")
    print("     - Dev profile: Skip mypy (~30s saved)")
    print("     - Strict profile: Skip mypy, pytest, npm test, ci-parity (~90s saved)")
    print("   • Impact: 30-90s time savings when basic linting fails")


def demo_validation():
    """Demo dependency rule validation"""
    print("\n✅ Dependency Rule Validation")
    print("-" * 40)

    errors = validate_dependency_rules()

    if errors:
        print("❌ Validation errors found:")
        for error in errors:
            print(f"   • {error}")
    else:
        print("✅ All dependency rules are valid!")
        print("   • No circular dependencies")
        print("   • All referenced checks exist")
        print("   • No self-dependencies")


async def demo_orchestrator_integration():
    """Demo integration with the cached orchestrator"""
    print("\n🔧 Orchestrator Integration Demo")
    print("-" * 40)

    # Create a temporary "broken" Python file to trigger ruff failure
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)

        # Create a Python file with syntax errors
        broken_file = repo_dir / "broken.py"
        broken_file.write_text(
            """
# This file has intentional errors to trigger ruff failure
import unused_module  # unused import
def broken_function(x,):  # trailing comma
    print("hello"  # missing closing paren
    return x
"""
        )

        # Create a pyproject.toml to make it look like a Python project
        (repo_dir / "pyproject.toml").write_text(
            """[tool.ruff]
select = ["E", "F", "W"]
"""
        )

        print("📁 Created test project with intentional syntax errors")
        print("🔄 Running checks to demonstrate dependency skipping...")

        try:
            # Run checks that include dependencies
            checks = ["ruff", "mypy", "pytest"]

            result = await run_checks_for_profile(
                repo_root=str(repo_dir),
                checks=checks,
                use_cache=False,  # Disable cache for demo
                profile="dev",  # Use dev profile (flexible dependencies)
            )

            print("\n📊 Results:")
            for check, info in result.items():
                status = info.get("status", "unknown")
                if status == "skipped":
                    reason = info.get("reason", "No reason provided")
                    print(f"   ⏭️  {check}: SKIPPED - {reason}")
                elif status == "ok":
                    print(f"   ✅ {check}: OK")
                elif status == "fail":
                    print(f"   ❌ {check}: FAILED")
                else:
                    print(f"   ❓ {check}: {status}")

            # Show what would happen in strict mode
            print("\n🔄 Same scenario in STRICT profile:")
            result_strict = await run_checks_for_profile(
                repo_root=str(repo_dir),
                checks=checks,
                use_cache=False,
                profile="strict",
            )

            for check, info in result_strict.items():
                status = info.get("status", "unknown")
                if status == "skipped":
                    reason = info.get("reason", "No reason provided")
                    print(f"   ⏭️  {check}: SKIPPED - {reason}")
                elif status == "ok":
                    print(f"   ✅ {check}: OK")
                elif status == "fail":
                    print(f"   ❌ {check}: FAILED")
                else:
                    print(f"   ❓ {check}: {status}")

        except Exception as e:
            print(f"⚠️  Demo integration failed: {e}")
            print("   (Expected - orchestrator may need actual tool commands)")


def demo_insights():
    """Demo comprehensive dependency insights"""
    print("\n🔍 Dependency System Insights")
    print("-" * 40)

    all_checks = ["ruff", "black", "mypy", "pytest", "npm test", "ci-parity"]
    insights = get_dependency_insights(all_checks)

    print("📊 System Overview:")
    print(f"   • Total dependency rules: {insights['total_rules']}")
    print(f"   • Strict rules: {insights['strict_rules']}")
    print(f"   • Flexible rules: {insights['flexible_rules']}")
    print(f"   • Execution levels: {insights['execution_levels']}")
    print(f"   • Checks per level: {insights['checks_per_level']}")

    if insights["most_critical_prerequisite"]:
        critical_check, count = insights["most_critical_prerequisite"]
        print(f"   • Most critical check: '{critical_check}' (blocks {count} others)")

    if insights["validation_errors"]:
        print(f"   ⚠️  Validation errors: {len(insights['validation_errors'])}")
    else:
        print("   ✅ Configuration is valid")


async def main():
    """Run all dependency demos"""
    print("🚀 FirstTry Step 4: Conditional Check Dependencies Demo")
    print("=" * 60)

    # Demo 1: Rules configuration
    demo_dependency_rules()

    # Demo 2: Dependency graph
    demo_dependency_graph()

    # Demo 3: Execution order
    demo_execution_order()

    # Demo 4: Skip logic scenarios
    demo_skip_logic()

    # Demo 5: Impact analysis
    demo_impact_analysis()

    # Demo 6: Validation
    demo_validation()

    # Demo 7: Orchestrator integration
    await demo_orchestrator_integration()

    # Demo 8: System insights
    demo_insights()

    print("\n🎉 Step 4 Complete!")
    print("Conditional check dependencies implemented with intelligent fail-fast logic,")
    print("flexible/strict modes, and significant time savings when prerequisites fail.")


if __name__ == "__main__":
    asyncio.run(main())
