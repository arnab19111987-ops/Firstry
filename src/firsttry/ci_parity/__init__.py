"""CI parity helpers for FirstTry (minimal, safe stubs).

This package provides a small, testable surface so `python -m firsttry.ci_parity.runner`
and the CLI hooks can import the expected names. Implementations are lightweight
and intentionally non-destructive.
"""

from .intents import autofill_intents, lint_intents
from .runner import main as runner_main

# Backwards-compatible alias: older code imports `parity_runner`.
# Export a `parity_runner` symbol that matches the historical API
# (it is the same callable as `runner_main`).
parity_runner = runner_main

__all__ = ["runner_main", "parity_runner", "lint_intents", "autofill_intents"]
