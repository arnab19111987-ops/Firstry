#!/usr/bin/env python3
"""
Demo of Step 7: Smart pytest integration with profiles
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.run_profiles import select_checks, get_pytest_mode_for_profile
from firsttry.cached_orchestrator import run_checks_for_profile


async def demo_step7_smart_pytest():
    """Demo the Step 7 smart pytest system"""
    repo_root = str(Path(__file__).parent)

    print("🚀 Step 7: Smart pytest Integration Demo")
    print("=" * 50)

    # Test different profiles with pytest
    profiles = ["fast", "dev", "full"]

    for profile in profiles:
        print(f"\n🎯 Testing profile: {profile}")

        # Show what checks are selected
        checks = select_checks(profile)
        print(f"   Selected checks: {', '.join(checks)}")

        # Show pytest mode for this profile
        if "pytest" in checks:
            pytest_mode = get_pytest_mode_for_profile(profile)
            print(f"   Pytest mode: {pytest_mode}")

        # Run with smart pytest
        print(f"\n--- Running {profile} profile with smart pytest ---")
        try:
            results = await run_checks_for_profile(
                repo_root=repo_root,
                checks=checks,
                use_cache=True,
                profile=profile,
                changed_files=["src/firsttry/cli.py"],  # Simulate change
            )

            # Show results summary
            success_count = sum(1 for r in results.values() if r.get("status") == "ok")
            cached_count = sum(1 for r in results.values() if r.get("cached"))
            total_count = len(results)

            print(f"\n📊 Profile {profile} Results:")
            print(f"   ✅ Success: {success_count}/{total_count}")
            print(f"   ⚡ Cached: {cached_count}/{total_count}")

            # Show pytest-specific results if present
            if "pytest" in results:
                pytest_result = results["pytest"]
                if pytest_result.get("cached"):
                    print("   🧪 Pytest: cached result")
                elif pytest_result.get("test_files"):
                    test_count = len(pytest_result["test_files"])
                    duration = pytest_result.get("duration", 0)
                    print(f"   🧪 Pytest: {test_count} test files, {duration:.2f}s")
                else:
                    print(f"   🧪 Pytest: {pytest_result.get('status', 'unknown')}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print("=" * 50)

    print("\n🎉 Step 7 Demo Complete!")
    print("Smart pytest system successfully integrated with:")
    print("  • Profile-based pytest modes (smoke/smart/full)")
    print("  • Change-based test targeting")
    print("  • Failed test prioritization")
    print("  • Cache-aware test execution")


if __name__ == "__main__":
    asyncio.run(demo_step7_smart_pytest())
