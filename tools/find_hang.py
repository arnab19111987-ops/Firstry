#!/usr/bin/env python3
"""Helper to bisect pytest test list and find a hanging test.

Usage: python tools/find_hang.py

It collects tests with `pytest --collect-only -q`, then runs halves of the
list recursively with a short timeout to locate the first test that hangs.
This avoids shell loops and uses Python's subprocess timeout handling.
"""

from __future__ import annotations

import subprocess
import sys


def collect_tests() -> list[str]:
    out = subprocess.check_output(["pytest", "--collect-only", "-q"])
    return [line.strip() for line in out.decode().splitlines() if line.strip()]


def run_nodes(nodes: list[str], timeout: int = 20) -> bool:
    if not nodes:
        return True
    cmd = ["pytest", "-q"] + nodes
    try:
        print(f"Running {len(nodes)} tests (first: {nodes[0]})")
        subprocess.run(cmd, check=True, timeout=timeout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Tests failed (exit {e.returncode}) for slice starting {nodes[0]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"TimeoutExpired for slice starting {nodes[0]} (hang suspected)")
        return False


def bisect_find(nodes: list[str]) -> str | None:
    # if the whole slice is OK, return None
    if run_nodes(nodes):
        return None

    if len(nodes) == 1:
        return nodes[0]

    mid = len(nodes) // 2
    left = nodes[:mid]
    right = nodes[mid:]

    print(f"Bisecting: left {len(left)} tests, right {len(right)} tests")

    found = bisect_find(left)
    if found:
        return found
    return bisect_find(right)


def main() -> int:
    nodes = collect_tests()
    print(f"Collected {len(nodes)} tests")
    culprit = bisect_find(nodes)
    if culprit:
        print("\nHANGING TEST FOUND:", culprit)
        return 0
    print("\nNo hanging test found (all slices completed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
