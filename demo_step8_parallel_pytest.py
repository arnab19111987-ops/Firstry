#!/usr/bin/env python3
"""
Demo of Step 8: Parallel pytest chunks system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.parallel_pytest import (
    analyze_test_suite,
    create_test_chunks,
    discover_all_tests,
    run_parallel_pytest,
)


async def demo_step8_parallel_pytest():
    """Demo the Step 8 parallel pytest chunking system"""
    repo_root = str(Path(__file__).parent)

    print("🚀 Step 8: Parallel pytest Chunks Demo")
    print("=" * 50)

    # Analyze the test suite
    print("📊 Analyzing test suite...")
    analysis = analyze_test_suite(repo_root)

    print(f"   Total test files: {analysis['total_files']}")
    print(f"   Estimated tests: {analysis['total_tests']}")
    print(f"   Chunking recommended: {analysis['chunking_recommended']}")

    if analysis["sample_counts"]:
        print("   Sample test counts:")
        for file, count in list(analysis["sample_counts"].items())[:3]:
            print(f"     {file}: {count} tests")

    # Show test discovery
    test_files = discover_all_tests(repo_root)
    print("\n🔍 Test Discovery:")
    print(f"   Found {len(test_files)} test files")
    if test_files:
        print("   Examples:")
        for test_file in test_files[:5]:
            print(f"     {test_file}")
        if len(test_files) > 5:
            print(f"     ... and {len(test_files) - 5} more")

    # Show chunking strategy
    if test_files:
        chunks = create_test_chunks(test_files, max_workers=4)
        print("\n🧩 Chunking Strategy:")
        print(f"   Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"     Chunk {i}: {len(chunk)} files")

    # Test parallel execution
    if analysis["total_files"] > 0:
        print("\n🏃 Testing Parallel Execution:")

        try:
            # Test with small subset to avoid long runs
            sample_files = test_files[:6] if len(test_files) > 6 else test_files

            result = await run_parallel_pytest(
                repo_root=repo_root,
                test_files=sample_files,
                max_workers=2,
                use_cache=True,
            )

            print("📊 Parallel Execution Results:")
            print(f"   Status: {result['status']}")
            print(f"   Chunking used: {result.get('chunking_used', False)}")

            if result.get("chunking_used"):
                print(f"   Chunks: {result.get('chunk_count', 0)}")
                print(f"   Total files: {result.get('total_files', 0)}")
                print(f"   Duration: {result.get('total_duration', 0):.2f}s")
                print(f"   Successful chunks: {result.get('successful_chunks', 0)}")
                print(f"   Failed chunks: {result.get('failed_chunks', 0)}")
            else:
                print("   Single execution mode")
                print(f"   Duration: {result.get('duration', 0):.2f}s")
                print(f"   Files: {result.get('file_count', 0)}")

            if result.get("cached"):
                print("   ⚡ Used cached result")

            # Show output preview
            output = result.get("output", "")
            if output:
                lines = output.split("\n")[:8]
                print("\n📝 Output Preview:")
                for line in lines:
                    if line.strip():
                        print(f"    {line}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n🎉 Step 8 Demo Complete!")
    print("Parallel pytest system features:")
    print("  • Automatic test suite analysis")
    print("  • Intelligent chunking for large suites (>200 tests)")
    print("  • Parallel chunk execution with result aggregation")
    print("  • Fallback to single execution for small suites")
    print("  • Cache-aware with chunk-level caching")


if __name__ == "__main__":
    asyncio.run(demo_step8_parallel_pytest())
