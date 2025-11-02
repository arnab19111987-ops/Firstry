#!/usr/bin/env python3
"""
Quick validation of the caching system performance
"""

import asyncio
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.run_profiles import select_checks
from firsttry.cached_orchestrator import run_checks_for_profile


async def test_cache_performance():
    """Test cache performance with a simple profile"""
    repo_root = str(Path(__file__).parent)
    
    print("🧪 FirstTry Cache Performance Test")
    print("=" * 40)
    
    # Use fast profile to test basic caching
    checks = ["repo_sanity"]  # Simple check that should pass
    
    print(f"Testing with check: {checks[0]}")
    
    # First run - cache miss
    print("\n--- First run (populating cache) ---")
    start = time.time()
    results1 = await run_checks_for_profile(
        repo_root=repo_root,
        checks=checks,
        use_cache=True
    )
    first_time = time.time() - start
    
    # Second run - cache hit
    print("\n--- Second run (using cache) ---")
    start = time.time()
    results2 = await run_checks_for_profile(
        repo_root=repo_root,
        checks=checks,
        use_cache=True
    )
    second_time = time.time() - start
    
    # Third run - cache disabled
    print("\n--- Third run (cache disabled) ---")
    start = time.time()
    results3 = await run_checks_for_profile(
        repo_root=repo_root,
        checks=checks,
        use_cache=False
    )
    third_time = time.time() - start
    
    print(f"\n📊 Performance Results:")
    print(f"  First run (cache miss): {first_time:.3f}s")
    print(f"  Second run (cache hit): {second_time:.3f}s")
    print(f"  Third run (no cache):   {third_time:.3f}s")
    
    if second_time < first_time:
        speedup = first_time / second_time
        print(f"  🚀 Cache speedup: {speedup:.1f}x faster")
    
    cached_count = sum(1 for r in results2.values() if r.get("cached"))
    print(f"  ⚡ Cached checks: {cached_count}/{len(checks)}")


if __name__ == "__main__":
    asyncio.run(test_cache_performance())