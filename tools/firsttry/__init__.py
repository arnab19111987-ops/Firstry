"""Thin wrapper so downstream tooling can import `tools.firsttry`
but we do NOT duplicate logic and drift.

All real code lives in top-level `firsttry` package.
"""

from firsttry import *  # noqa: F403
