#!/usr/bin/env python3
"""Calculate typing crutches baseline (Any, ignore, cast) in source code."""

import re
from collections import defaultdict
from pathlib import Path


def count_typing_crutches(directory: str = "src") -> dict[str, int]:
    """Count typing crutches in Python source files."""
    counts = defaultdict(int)

    # Patterns to match typing crutches
    patterns = {
        "any": r"\bAny\b",  # Type[Any], x: Any, etc.
        "ignore": r"#\s*type:\s*ignore",  # type: ignore comments
        "cast": r"\bcast\s*\(",  # cast( function calls
    }

    # Walk through all Python files
    for pyfile in Path(directory).rglob("*.py"):
        try:
            with open(pyfile, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for crutch, pattern in patterns.items():
                matches = re.findall(pattern, content)
                counts[crutch] += len(matches)
        except Exception:
            pass

    return dict(counts)


if __name__ == "__main__":
    counts = count_typing_crutches()

    # Ensure all crutches are in output even if count is 0
    crutches = ["any", "ignore", "cast"]
    for crutch in crutches:
        count = counts.get(crutch, 0)
        print(f"{crutch}={count}")
