"""Helper utilities for CI intent manipulation (stubs)."""


def normalize_intent(data):
    return data


def cli_autofill_intents(path: str | None = None) -> int:
    """CLI helper to autofill intents into a CI mirror file.

    Minimal, safe stub used by the CLI when the full implementation
    is not needed in tests.
    """
    # No-op autofill; return success
    return 0


def cli_lint_intents(path: str | None = None) -> int:
    """CLI helper to lint intents. Minimal stub that always succeeds."""
    return 0
