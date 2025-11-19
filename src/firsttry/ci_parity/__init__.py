"""CI parity helpers for FirstTry (minimal, safe stubs).

This package provides a small, testable surface so `python -m firsttry.ci_parity.runner`
and the CLI hooks can import the expected names. Implementations are lightweight
and intentionally non-destructive.
"""

from .intents import autofill_intents, lint_intents
from .runner import main as runner_main

__all__ = ["runner_main", "lint_intents", "autofill_intents"]
