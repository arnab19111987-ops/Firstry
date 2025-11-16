# src/firsttry/reports/tier_map.py

"""
Tier metadata and feature mapping.

This module defines:
- Canonical tiers and their titles/subtitles (TIER_META)
- Checks allowed per tier (TIER_CHECKS)
- Legacy tier mappings (LEGACY_TIER_CHECKS)
- Helper functions for resolving checks and metadata
"""

# Canonical tier → pretty name → subtitle
TIER_META = {
    "free-lite": {
        "title": "FirstTry — Free Lite",
        "subtitle": "Level 1 · Developer (Lite) · Free forever",
    },
    "free-strict": {
        "title": "FirstTry — Free Strict",
        "subtitle": "Level 2 · Developer (Strict) · Free forever",
    },
    "pro": {
        "title": "FirstTry — Pro",
        "subtitle": "Level 3 · Teams (Pro) · License required",
    },
    "promax": {
        "title": "FirstTry — ProMax",
        "subtitle": "Level 4 · Teams (ProMax) · License required",
    },
}

# What each canonical tier is allowed to run
TIER_CHECKS = {
    # Fastest / "just tell me if it's obviously wrong"
    "free-lite": ["ruff"],
    # Stricter developer checks
    "free-strict": ["ruff", "mypy", "pytest"],
    # Teams / Pro checks
    "pro": ["ruff", "mypy", "pytest", "bandit", "pip-audit", "ci-parity"],
    # ProMax / Enterprise checks
    "promax": [
        "ruff",
        "mypy",
        "pytest",
        "bandit",
        "pip-audit",
        "ci-parity",
        "coverage",
        "secrets-scan",
    ],
}

# Used by reports/UX when a feature is locked to paid tiers.
# Keep this consistent with CLI messages in src/firsttry/cli.py.
LOCKED_MESSAGE = (
    "🔒 Locked — available in Pro / ProMax. "
    "Set FIRSTTRY_LICENSE_KEY=... or run `firsttry license activate`."
)

# Legacy tier mappings for backward compatibility
LEGACY_TIER_CHECKS = {
    "free": ["ruff", "mypy", "pytest"],
    "developer": ["ruff", "mypy", "pytest"],
    "teams": ["ruff", "mypy", "pytest", "bandit", "pip-audit", "ci-parity"],
    "enterprise": [
        "ruff",
        "mypy",
        "pytest",
        "bandit",
        "pip-audit",
        "ci-parity",
        "coverage",
        "secrets-scan",
    ],
}


def get_checks_for_tier(tier: str) -> list[str]:
    """Return the list of checks allowed for a given tier.

    Prefers the new canonical tier names, but falls back to legacy
    tier names if needed. Defaults to the free-lite set.
    """
    # First try new tier system
    if tier in TIER_CHECKS:
        return TIER_CHECKS[tier]
    # Fall back to legacy tier names
    if tier in LEGACY_TIER_CHECKS:
        return LEGACY_TIER_CHECKS[tier]
    # Default fallback
    return TIER_CHECKS["free-lite"]


def get_tier_meta(tier: str) -> dict:
    """Return title/subtitle metadata for a given tier."""
    if tier in TIER_META:
        return TIER_META[tier]
    # Legacy fallback
    legacy_meta = {
        "free": {"title": "FirstTry — Free", "subtitle": "Legacy free tier"},
        "developer": {
            "title": "FirstTry — Developer",
            "subtitle": "Legacy developer tier",
        },
        "teams": {"title": "FirstTry — Teams", "subtitle": "Legacy teams tier"},
        "enterprise": {
            "title": "FirstTry — Enterprise",
            "subtitle": "Legacy enterprise tier",
        },
    }
    return legacy_meta.get(tier, TIER_META["free-lite"])


def is_tier_free(tier: str) -> bool:
    """Return True if the tier is considered free (no license required)."""
    return tier in ("free-lite", "free-strict", "free", "developer")


def is_tier_paid(tier: str) -> bool:
    """Return True if the tier is considered paid (license required)."""
    return tier in ("pro", "promax", "teams", "enterprise")


# Legacy compatibility alias
LOCK_MESSAGE = LOCKED_MESSAGE
