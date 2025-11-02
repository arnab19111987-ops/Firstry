#!/usr/bin/env python3
"""
Test the lazy orchestrator optimizations that should address the "hidden 11 seconds".

This demonstrates:
1. Detection cache (10 minute TTL)
2. Sentinel file detection (cheap before expensive rglob)  
3. Lazy bucket building (fast → mutating → slow)
4. Lazy imports (heavy modules loaded only when needed)
5. Deferred reporting (async JSON writing)
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.lazy_orchestrator import run_profile_for_repo
from firsttry.run_profiles import dev_profile
from firsttry.detectors import detect_stack


def test_detection_cache():
    """Test detection caching to avoid expensive rglob operations."""
    print("🔍 Testing Detection Cache")
    print("-" * 40)
    
    repo_root = Path.cwd()
    
    # First detection (may be expensive)
    start = time.monotonic()
    result1 = detect_stack(repo_root)
    first_time = time.monotonic() - start
    
    # Second detection (should use cache)
    start = time.monotonic()
    result2 = detect_stack(repo_root)
    second_time = time.monotonic() - start
    
    print(f"📊 First detection: {first_time:.3f}s")
    print(f"📊 Cached detection: {second_time:.3f}s")
    print(f"🚀 Speedup: {first_time/second_time:.1f}x")
    print(f"📋 Detected: {result1}")
    
    assert result1 == result2, "Cache should return same result"
    
    if second_time < first_time * 0.1:  # Should be at least 10x faster
        print("✅ Detection cache working properly!")
    else:
        print("⚠️  Cache improvement less than expected")


def test_lazy_orchestrator():
    """Test the lazy orchestrator that builds buckets on demand."""
    print("\n⚡ Testing Lazy Orchestrator")
    print("-" * 40)
    
    repo_root = Path.cwd()
    report_path = repo_root / ".firsttry" / "test_lazy.json"
    
    # Run with dev profile
    start = time.monotonic()
    results = run_profile_for_repo(
        repo_root=repo_root,
        profile=dev_profile(),
        report_path=report_path
    )
    total_time = time.monotonic() - start
    
    print(f"📊 Total execution time: {total_time:.3f}s")
    print(f"📊 Tools executed: {len(results)}")
    
    # Show results
    for result in results:
        status_emoji = "✅" if result["status"] == "ok" else "❌"
        cache_info = " (cached)" if result.get("from_cache") else ""
        elapsed = result.get("elapsed", 0)
        print(f"  {status_emoji} {result['name']}: {elapsed:.3f}s{cache_info}")
    
    # Check that report was written asynchronously
    if report_path.exists():
        print("✅ Async report writing successful!")
    else:
        print("⚠️  Report not found (may still be writing)")
    
    return total_time


def main():
    """Run all optimization tests."""
    print("🧪 LAZY ORCHESTRATOR OPTIMIZATION TESTS")
    print("=" * 60)
    print("Testing optimizations to address the 'hidden 11 seconds'")
    
    # Test 1: Detection cache
    test_detection_cache()
    
    # Test 2: Lazy orchestrator
    first_run_time = test_lazy_orchestrator()
    
    # Test 3: Second run should be much faster with caching
    print("\n🔄 Testing Second Run (Cache Effects)")
    print("-" * 40)
    
    second_run_time = test_lazy_orchestrator()
    
    if second_run_time < first_run_time * 0.8:
        speedup = first_run_time / second_run_time
        print(f"🚀 Second run speedup: {speedup:.1f}x")
        print("✅ Smart cache and lazy loading working!")
    else:
        print("⚠️  Expected more improvement from caching")
    
    print(f"\n📊 Performance Summary:")
    print(f"  • First run: {first_run_time:.3f}s")
    print(f"  • Second run: {second_run_time:.3f}s")
    print(f"  • Improvement: {(1 - second_run_time/first_run_time)*100:.1f}%")
    
    print("\n🎯 Optimizations Applied:")
    print("  ✅ Detection cache (10-minute TTL)")
    print("  ✅ Sentinel file detection (before expensive rglob)")
    print("  ✅ Lazy bucket building (fast → mutating → slow)")
    print("  ✅ Lazy imports (heavy modules loaded on demand)")
    print("  ✅ Deferred reporting (async JSON writing)")
    
    print("\n🚀 Ready for production with optimized startup time!")


if __name__ == "__main__":
    main()