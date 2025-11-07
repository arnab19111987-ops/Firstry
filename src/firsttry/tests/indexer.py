"""Pytest collection and indexing for test pruning.

Builds an index of all test nodeids in the project and maps them to their
source file dependencies. This allows efficient test selection based on
changed files.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Dict
from typing import List
from typing import Set

INDEX_CACHE_DIR = ".firsttry/cache"
PYTEST_INDEX_FILE = os.path.join(INDEX_CACHE_DIR, "pytest_index.json")


def collect_tests() -> List[str]:
    """Collect all pytest test nodeids using pytest --collect-only.

    Returns:
        List of test nodeids (e.g., ["tests/test_foo.py::test_bar", ...])
    """
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Parse output to extract nodeids
        lines = result.stdout.split("\n")
        nodeids = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(" ") and "::" in line:
                nodeids.append(line)
        return nodeids
    except Exception as e:
        print(f"[pytest_indexer] Warning: Failed to collect tests: {e}")
        return []


def build_test_file_map() -> Dict[str, Set[str]]:
    """Build map of test file -> set of test nodeids.

    Returns:
        Dict mapping test file paths to sets of nodeids
    """
    nodeids = collect_tests()
    test_map: Dict[str, Set[str]] = {}

    for nodeid in nodeids:
        # Extract file path (part before ::)
        parts = nodeid.split("::")
        if parts:
            test_file = parts[0]
            if test_file not in test_map:
                test_map[test_file] = set()
            test_map[test_file].add(nodeid)

    return test_map


def save_index(test_map: Dict[str, Set[str]]) -> None:
    """Save test index to cache file.

    Args:
        test_map: Test file -> nodeid set mapping
    """
    os.makedirs(INDEX_CACHE_DIR, exist_ok=True)
    # Convert sets to sorted lists for JSON serialization
    serializable = {k: sorted(v) for k, v in test_map.items()}
    with open(PYTEST_INDEX_FILE, "w") as f:
        json.dump(serializable, f, separators=(",", ":"))


def load_index() -> Dict[str, Set[str]]:
    """Load test index from cache file.

    Returns:
        Test file -> nodeid set mapping, or empty dict if not found
    """
    if not os.path.exists(PYTEST_INDEX_FILE):
        return {}
    try:
        with open(PYTEST_INDEX_FILE, "r") as f:
            data = json.load(f)
        # Convert lists back to sets
        return {k: set(v) for k, v in data.items()}
    except Exception:
        return {}


def get_or_build_index() -> Dict[str, Set[str]]:
    """Get test index from cache or build if not present.

    Returns:
        Test file -> nodeid set mapping
    """
    cached = load_index()
    if cached:
        return cached

    # Build and cache
    test_map = build_test_file_map()
    save_index(test_map)
    return test_map
