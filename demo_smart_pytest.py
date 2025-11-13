#!/usr/bin/env python3
"""
Demo of the smart pytest system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from firsttry.smart_pytest import (
    build_pytest_command,
    get_failed_tests,
    get_smoke_tests,
    get_test_files_for_changes,
    has_pytest_xdist,
    run_smart_pytest,
)


async def demo_smart_pytest():
    """Demo the smart pytest functionality"""
    repo_root = str(Path(__file__).parent)

    print("🧪 Smart pytest Demo")
    print("=" * 40)

    # Check pytest-xdist availability
    has_xdist = has_pytest_xdist(repo_root)
    print(f"📦 pytest-xdist available: {has_xdist}")

    # Show smoke tests
    smoke_tests = get_smoke_tests(repo_root)
    print(f"💨 Smoke tests found: {smoke_tests}")

    # Show failed tests (if any)
    failed_tests = get_failed_tests(repo_root)
    print(f"❌ Previously failed tests: {len(failed_tests)} found")

    # Test change-based targeting
    changed_files = ["src/firsttry/cli.py", "tests/test_cli.py"]
    target_tests = get_test_files_for_changes(repo_root, changed_files)
    print(f"🎯 Target tests for changes {changed_files}: {target_tests}")

    # Build different command examples
    print("\n🔧 Command Examples:")

    smoke_cmd = build_pytest_command(repo_root, mode="smoke")
    print(f"  Smoke: {' '.join(smoke_cmd)}")

    failed_cmd = build_pytest_command(repo_root, mode="failed")
    print(f"  Failed: {' '.join(failed_cmd)}")

    smart_cmd = build_pytest_command(repo_root, mode="smart", test_files=list(target_tests))
    print(f"  Smart: {' '.join(smart_cmd)}")

    full_cmd = build_pytest_command(repo_root, mode="full")
    print(f"  Full: {' '.join(full_cmd)}")

    # Test smart pytest execution
    print("\n🚀 Running smart pytest...")
    try:
        result = await run_smart_pytest(
            repo_root=repo_root,
            changed_files=changed_files,
            mode="smart",
            use_cache=True,
        )

        print(f"📊 Result: {result['status']}")
        if result.get("cached"):
            print("⚡ Used cached result")
        else:
            print(f"⏱️  Duration: {result.get('duration', 0):.2f}s")
            print(f"🧪 Test files: {result.get('test_files', 'all')}")

        if result.get("output"):
            # Show first few lines of output
            output_lines = result["output"].split("\n")[:5]
            print("📝 Output preview:")
            for line in output_lines:
                if line.strip():
                    print(f"    {line}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(demo_smart_pytest())
