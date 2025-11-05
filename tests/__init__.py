"""Tests package marker.

This file makes the top-level `tests` a package so imports under `tests.*` are predictable
for runs that target the `tests` tree. Keep minimal; licensing/tests will map `tests` to
`licensing.tests` when running under that subtree.
"""

__all__ = []
"""Make the tests directory an importable package for pytest-run compatibility.

This allows tests to import "tests.<module>" safely during collection.
The file is intentionally minimal and safe for test runtime.
"""

__all__ = []
