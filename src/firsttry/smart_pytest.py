from __future__ import annotations
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set, Any

from . import cache as ft_cache
from .parallel_pytest import run_parallel_pytest, analyze_test_suite


def get_pytest_cache_dir(repo_root: str) -> Path:
    """Get pytest cache directory for failed test tracking"""
    return Path(repo_root) / ".pytest_cache"


def get_failed_tests(repo_root: str) -> List[str]:
    """Get list of previously failed tests from pytest cache"""
    cache_dir = get_pytest_cache_dir(repo_root)
    failed_file = cache_dir / "v" / "cache" / "lastfailed"

    if not failed_file.exists():
        return []

    try:
        with failed_file.open("r") as f:
            failed_data = json.load(f)
        # Extract test node IDs (keys from the failed dict)
        return list(failed_data.keys())
    except Exception:
        return []


def get_test_files_for_changes(repo_root: str, changed_files: List[str]) -> Set[str]:
    """Map changed source files to relevant test files"""
    repo_path = Path(repo_root)
    test_files = set()

    for changed_file in changed_files:
        if not changed_file.endswith(".py"):
            continue

        changed_path = Path(changed_file)

        # Direct test file mapping strategies:
        # 1. If it's already a test file, include it
        if (
            "test_" in changed_path.name
            or changed_path.name.endswith("_test.py")
            or "tests/" in str(changed_path)
        ):
            test_files.add(changed_file)
            continue

        # 2. Look for corresponding test files
        # Example: src/mymodule.py -> tests/test_mymodule.py
        potential_test_names = [
            f"test_{changed_path.stem}.py",
            f"{changed_path.stem}_test.py",
        ]

        # Search in common test directories
        test_dirs = ["tests", "test", "src/tests"]
        for test_dir in test_dirs:
            test_dir_path = repo_path / test_dir
            if test_dir_path.exists():
                for test_name in potential_test_names:
                    test_file = test_dir_path / test_name
                    if test_file.exists():
                        test_files.add(str(test_file.relative_to(repo_path)))

        # 3. Look for tests in the same directory
        same_dir = changed_path.parent
        for test_name in potential_test_names:
            test_file = same_dir / test_name
            if test_file.exists():
                test_files.add(str(test_file.relative_to(repo_path)))

    return test_files


def get_smoke_tests(repo_root: str) -> List[str]:
    """Get smoke tests - fast tests that validate basic functionality"""
    repo_path = Path(repo_root)
    smoke_tests = []

    # Look for common smoke test patterns
    smoke_patterns = [
        "tests/test_smoke.py",
        "tests/smoke/",
        "test/smoke/",
        "tests/test_basic.py",
        "tests/test_imports.py",
    ]

    for pattern in smoke_patterns:
        path = repo_path / pattern
        if path.exists():
            if path.is_file():
                smoke_tests.append(pattern)
            elif path.is_dir():
                # Add all test files in smoke directory
                for test_file in path.glob("test_*.py"):
                    smoke_tests.append(str(test_file.relative_to(repo_path)))

    # If no dedicated smoke tests, pick a few fast ones
    if not smoke_tests:
        test_dirs = ["tests", "test"]
        for test_dir in test_dirs:
            test_dir_path = repo_path / test_dir
            if test_dir_path.exists():
                # Get first few test files as smoke tests
                test_files = list(test_dir_path.glob("test_*.py"))[:3]
                smoke_tests.extend(str(f.relative_to(repo_path)) for f in test_files)
                break

    return smoke_tests


def has_pytest_xdist(repo_root: str) -> bool:
    """Check if pytest-xdist is available for parallel execution"""
    try:
        result = subprocess.run(
            ["python", "-c", "import xdist"],
            cwd=repo_root,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def build_pytest_command(
    repo_root: str,
    test_files: List[str] = None,
    failed_only: bool = False,
    parallel: bool = True,
    mode: str = "smart",  # smart, smoke, full, failed
) -> List[str]:
    """Build optimized pytest command based on mode and available features"""

    cmd = ["python", "-m", "pytest"]

    # Base flags for better output
    cmd.extend(["-v", "--tb=short"])

    # Mode-specific configuration
    if mode == "smoke":
        # Fast smoke tests only
        smoke_tests = get_smoke_tests(repo_root)
        if smoke_tests:
            cmd.extend(smoke_tests)
        cmd.extend(["-x", "--maxfail=1"])  # Stop on first failure

    elif mode == "failed":
        # Only previously failed tests
        cmd.append("--lf")  # last failed

    elif mode == "smart":
        # Smart mode: failed tests first, then changed-related
        failed_tests = get_failed_tests(repo_root)
        if failed_tests:
            cmd.append("--lf")  # Run failed tests first
        elif test_files:
            cmd.extend(test_files)
        else:
            # Fall back to smoke tests
            smoke_tests = get_smoke_tests(repo_root)
            if smoke_tests:
                cmd.extend(smoke_tests)

    elif mode == "full":
        # Full test suite
        pass  # Run everything

    elif mode == "parallel":
        # Use parallel chunking for large test suites
        pass  # Handled by run_parallel_pytest

    # Add specific test files if provided
    if test_files and mode not in ["smoke", "failed"]:
        cmd.extend(test_files)

    # Parallel execution if available and beneficial
    if parallel and has_pytest_xdist(repo_root):
        # Use auto-detection for worker count
        cmd.extend(["-n", "auto"])

    return cmd


async def run_smart_pytest(
    repo_root: str,
    changed_files: List[str] | None = None,
    mode: str = "smart",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Run pytest with smart optimizations:
    - Cache-aware execution
    - Failed test prioritization
    - Change-based test targeting
    - Parallel execution when beneficial
    """

    # Check cache first if enabled
    if use_cache:
        # Build input hash from relevant test files and source files
        repo_path = Path(repo_root)
        test_patterns = ["tests/**/*.py", "test/**/*.py", "src/**/*.py", "**/*test*.py"]
        test_files: list = []
        for pattern in test_patterns:
            test_files.extend(repo_path.glob(pattern))

        input_hash = ft_cache.sha256_of_paths(test_files)

        if ft_cache.is_tool_cache_valid(repo_root, "pytest", input_hash):
            return {
                "status": "ok",
                "cached": True,
                "output": "Pytest results cached - no changes detected",
            }

    # Determine test files to run based on changes
    target_test_files = []
    if changed_files:
        target_test_files = list(get_test_files_for_changes(repo_root, changed_files))

    # Build optimized pytest command
    cmd = build_pytest_command(
        repo_root=repo_root, test_files=target_test_files, mode=mode, parallel=True
    )

    # Decide whether to use parallel execution
    if mode == "full" or (not target_test_files and mode == "smart"):
        # For full mode or smart mode with no specific targets, consider parallel execution
        analysis = analyze_test_suite(repo_root)

        if analysis["chunking_recommended"] and analysis["total_tests"] > 200:
            # Use parallel execution for large test suites
            return await run_parallel_pytest(
                repo_root=repo_root,
                test_files=target_test_files if target_test_files else None,
                use_cache=use_cache,
                extra_args=[],
            )

    # Execute pytest normally
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        duration = time.time() - start_time
        success = result.returncode == 0

        # Cache successful results
        if use_cache and success:
            ft_cache.write_tool_cache(
                repo_root,
                "pytest",
                input_hash,
                "ok",
                {"duration": duration, "test_count": len(target_test_files) or "all"},
            )

        return {
            "status": "ok" if success else "fail",
            "output": result.stdout + result.stderr,
            "duration": duration,
            "exit_code": result.returncode,
            "test_files": target_test_files,
            "command": cmd,
            "chunking_used": False,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "output": "Pytest timed out after 120 seconds",
            "duration": 120,
            "exit_code": 124,
        }
    except Exception as e:
        return {
            "status": "error",
            "output": f"Error running pytest: {e}",
            "duration": time.time() - start_time,
            "exit_code": 1,
        }
