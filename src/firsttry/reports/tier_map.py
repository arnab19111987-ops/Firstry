# src/firsttry/reports/tier_map.py

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

# what each tier is ALLOWED to see
TIER_CHECKS = {
    # fastest / "just tell me if it's stupid"
    "free-lite": ["ruff"],

    # your old "developer/free" set
    "free-strict": ["ruff", "mypy", "pytest"],

    # your old "teams/pro" set
    "pro": ["ruff", "mypy", "pytest", "bandit", "pip-audit", "ci-parity"],

    # your old "enterprise"
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

LOCKED_MESSAGE = (
    "🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock."
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
    # First try new tier system
    if tier in TIER_CHECKS:
        return TIER_CHECKS[tier]
    # Fall back to legacy tier names
    if tier in LEGACY_TIER_CHECKS:
        return LEGACY_TIER_CHECKS[tier]
    # Default fallback
    return TIER_CHECKS["free-lite"]


def get_tier_meta(tier: str) -> dict:
    if tier in TIER_META:
        return TIER_META[tier]
    # Legacy fallback
    legacy_meta = {
        "free": {"title": "FirstTry — Free", "subtitle": "Legacy free tier"},
        "developer": {"title": "FirstTry — Developer", "subtitle": "Legacy developer tier"},
        "teams": {"title": "FirstTry — Teams", "subtitle": "Legacy teams tier"},
        "enterprise": {"title": "FirstTry — Enterprise", "subtitle": "Legacy enterprise tier"},
    }
    return legacy_meta.get(tier, TIER_META["free-lite"])


def is_tier_free(tier: str) -> bool:
    return tier in ("free-lite", "free-strict", "free", "developer")


def is_tier_paid(tier: str) -> bool:
    return tier in ("pro", "promax", "teams", "enterprise")

# Legacy compatibility
LOCK_MESSAGE = LOCKED_MESSAGE