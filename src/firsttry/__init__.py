"""
FirstTry package init.

We intentionally keep this file minimal to avoid circular imports:
tests create a temporary firsttry/runners.py, then reload firsttry.cli
with FIRSTTRY_USE_REAL_RUNNERS=1. If __init__ imports cli eagerly,
it prevents that dynamic loading from working.

So we do NOT import cli, gates, etc. here.
"""

__version__ = "0.1.0"
