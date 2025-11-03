#!/usr/bin/env python3
"""
Demo of the new caching system for FirstTry.
This shows the cache-aware orchestrator in action.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.run_profiles import select_checks, get_profile_description
from firsttry.cached_orchestrator import run_checks_for_profile


async def demo_cached_runs():
    """Demo the caching system with different profiles"""
    repo_root = str(Path(__file__).parent)
    
    print("🚀 FirstTry Caching System Demo")
    print("=" * 50)
    
    # Test different profiles
    profiles = ["fast", "dev", "full"]
    
    for profile in profiles:
        print(f"\n🎯 Testing profile: {profile}")
        print(f"   Description: {get_profile_description(profile)}")
        
        checks = select_checks(profile)
        print(f"   Checks: {', '.join(checks)}")
        
        print("\n--- First run (cache miss) ---")
        results1 = await run_checks_for_profile(
            repo_root=repo_root,
            checks=checks,
            use_cache=True,
            profile=profile
        )
        
        print("\n--- Second run (cache hit) ---")
        results2 = await run_checks_for_profile(
            repo_root=repo_root,
            checks=checks,
            use_cache=True,
            profile=profile
        )
        
        # Count cached results
        cached_count = sum(1 for r in results2.values() if r.get("cached"))
        print(f"\n⚡ Cached {cached_count}/{len(checks)} checks on second run")
        
        print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(demo_cached_runs())