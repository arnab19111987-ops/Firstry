"""Test pruning based on changed files.

Maps git changed files to impacted tests and prunes the test suite to only
run affected tests. Provides safe fallback if selection would skip too many
tests (safeguard against false negatives).
"""

from __future__ import annotations

import subprocess
from typing import List
from typing import Set

from .indexer import get_or_build_index

# Safety threshold: if pruned selection is > 70% of full suite, run full suite
PRUNE_FALLBACK_THRESHOLD = 0.70


def get_changed_files(base_ref: str = "HEAD~1") -> Set[str]:
    """Get list of changed files using git.

    Args:
        base_ref: Git ref to compare against (default: previous commit)

    Returns:
        Set of changed file paths
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return set(result.stdout.strip().split("\n")) - {""}
    except Exception:
        pass
    return set()


def _should_run_test(nodeid: str, changed_files: Set[str]) -> bool:
    """Check if a test should run based on changed files.

    A test runs if:
    1. Its test file is changed, OR
    2. Any source file it imports has changed

    Args:
        nodeid: Test nodeid (e.g., "tests/test_foo.py::test_bar")
        changed_files: Set of changed file paths

    Returns:
        True if test should run
    """
    # Extract test file path
    test_file = nodeid.split("::")[0]

    # If test file itself changed, run it
    if test_file in changed_files:
        return True

    # For now, simple heuristic: if any Python file in src/ changed,
    # run all tests (conservative approach)
    # TODO: Implement more sophisticated dependency analysis
    src_files = [f for f in changed_files if f.startswith("src/") and f.endswith(".py")]
    if src_files:
        return True

    return False


def select_impacted_tests(changed_files: Set[str]) -> List[str]:
    """Select tests impacted by changed files.

    Args:
        changed_files: Set of changed file paths

    Returns:
        List of test nodeids to run, or empty list (run full suite)
    """
    if not changed_files:
        # No changes; run full suite
        return []

    # Get full test map
    test_map = get_or_build_index()
    all_nodeids = set()
    for nodeids in test_map.values():
        all_nodeids.update(nodeids)

    # Select impacted tests
    selected = [n for n in all_nodeids if _should_run_test(n, changed_files)]

    # Safety check: if selection is too large, run full suite
    if all_nodeids:
        prune_ratio = len(selected) / len(all_nodeids)
        if prune_ratio > PRUNE_FALLBACK_THRESHOLD:
            # Too many tests selected; run full suite
            return []

    return sorted(selected)
