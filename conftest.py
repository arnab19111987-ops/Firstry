"""Top-level pytest configuration helpers.

This adds an explicit collection-time ignore for the `benchmarks/` tree to
ensure malformed demo/benchmark files are never collected during test runs.
"""
from pathlib import Path


def pytest_ignore_collect(collection_path: Path, path, config=None):
    """Ignore collection for any path under `benchmarks/`.

    Use the modern hook signature `collection_path` to avoid pytest's
    deprecation warning about the legacy ``path`` parameter.
    """
    try:
        p = Path(collection_path)
    except Exception:
        return False

    # Skip anything under the benchmarks directory
    parts = p.parts if hasattr(p, "parts") else str(p)
    if isinstance(parts, tuple):
        if "benchmarks" in parts:
            return True
    else:
        if "benchmarks" in str(parts):
            return True
    return False
