#!/usr/bin/env python3
"""
Demo: Enhanced orchestrator with timing and cache invalidation
Step 12 of FirstTry performance optimization
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.cached_orchestrator import run_checks_for_profile


async def demo_enhanced_orchestrator():
    """Demonstrate enhanced orchestrator with timing and cache invalidation"""
    print("🚀 Step 12: Enhanced Orchestrator with Timing & Cache Invalidation")
    print("=" * 70)

    repo_root = str(Path(__file__).parent)

    # Test 1: Dev profile (fast checks only)
    print("\n📋 Test 1: Dev Profile (fast checks with timing)")
    print("-" * 50)

    try:
        results = await run_checks_for_profile(
            repo_root=repo_root,
            checks=["ruff", "mypy", "repo_sanity", "black_check"],
            use_cache=True,
            profile="dev",
        )

        print(f"\n✅ Dev profile completed - {len(results)} checks")

        # Analyze timing results
        total_time = 0
        cached_count = 0

        for check, result in results.items():
            elapsed = result.get("elapsed", 0)
            cached = result.get("cached", False)
            status = result.get("status", "unknown")

            if cached:
                cached_count += 1
                print(f"  • {check}: {status} (cached)")
            else:
                total_time += elapsed
                print(f"  • {check}: {status} ({elapsed:.2f}s)")

        print("\n📊 Performance Summary:")
        print(f"  • Total execution time: {total_time:.2f}s")
        print(f"  • Cached hits: {cached_count}/{len(results)}")
        print(f"  • Cache efficiency: {cached_count/len(results)*100:.1f}%")

    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("🎯 Enhanced orchestrator demo completed!")
    print("Key improvements:")
    print("  ✓ Per-check timing with millisecond precision")
    print("  ✓ Mutating cache invalidation logic")
    print("  ✓ 3-phase execution (fast → mutating → slow)")
    print("  ✓ Enhanced metadata storage in cache")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_orchestrator())
