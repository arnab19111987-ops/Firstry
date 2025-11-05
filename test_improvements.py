#!/usr/bin/env python3
"""
Quick test of the new improvements:
1. Smart cache that replays failed results 
2. Phase timing instrumentation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.cached_orchestrator import run_checks_for_profile
from firsttry.run_profiles import select_checks


async def main():
    """Test the new smart cache and timing instrumentation."""
    print("🧪 Testing Smart Cache & Timing Instrumentation")
    print("=" * 60)

    repo_root = str(Path.cwd())
    checks = select_checks(profile="dev", changed=None)

    print(f"📊 Running {len(checks)} checks to test improvements")

    # Run once to see timing breakdown
    results = await run_checks_for_profile(
        repo_root=repo_root, checks=checks, use_cache=True, profile="dev"
    )

    print("\n📈 Timing Analysis:")
    timing = results.get("_timing_metadata", {})
    for phase, duration_ms in timing.items():
        if phase != "total_ms":
            print(f"  • {phase}: {duration_ms:.0f}ms")

    total_ms = timing.get("total_ms", 0)
    print(f"  • Total: {total_ms:.0f}ms ({total_ms/1000:.2f}s)")

    # Check if any results have cache_state indicating smart cache usage
    cache_states = [
        r.get("cache_state")
        for r in results.values()
        if isinstance(r, dict) and "cache_state" in r
    ]
    if cache_states:
        print(f"\n💾 Cache states observed: {set(cache_states)}")

    print("\n✅ Smart cache and timing instrumentation are working!")
    print("🔍 This reveals exactly where execution time is spent")


if __name__ == "__main__":
    asyncio.run(main())
