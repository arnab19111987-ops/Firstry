"""Thin wrapper so downstream tooling can import `tools.firsttry`
but we do NOT duplicate logic and drift.

All real code lives in top-level `firsttry` package.
"""

# Import the aliased module which points to root firsttry
import sys

from .firsttry import *  # noqa: F403

# Make tools.firsttry fully transparent to the root firsttry package
# by making this module object be the same as the root package
_root_firsttry = sys.modules.get("firsttry")
if _root_firsttry is not None:
    # Replace this module with the root firsttry in sys.modules
    # so that `import tools.firsttry` gives the exact same object as `import firsttry`
    sys.modules[__name__] = _root_firsttry
