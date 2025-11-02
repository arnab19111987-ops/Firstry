# src/firsttry/license_guard.py

from __future__ import annotations

import os
from typing import Optional

# ---------------------------------------------------------------------------
# Canonical tier names (new)
# ---------------------------------------------------------------------------
# free forever
FREE_TIERS = ("free-lite", "free-strict")
# paid / locked
PAID_TIERS = ("pro", "promax")

# All accepted synonyms → canonical
TIER_SYNONYMS = {
    # ----- free-lite -----
    "free": "free-lite",
    "free-lite": "free-lite",
    "lite": "free-lite",
    "dev": "free-lite",
    "developer": "free-lite",
    "fast": "free-lite",
    "auto": "free-lite",

    # ----- free-strict -----
    "free-strict": "free-strict",
    "strict": "free-strict",
    "ci": "free-strict",
    "config": "free-strict",
    "verify": "free-strict",

    # ----- pro (paid) -----
    "pro": "pro",
    "team": "pro",
    "teams": "pro",
    "full": "pro",

    # ----- promax (paid) -----
    "promax": "promax",
    "enterprise": "promax",
    "org": "promax",
}


class LicenseError(RuntimeError):
    """Raised when a paid tier is used without a valid license."""
    pass


def normalize_tier(raw: Optional[str]) -> str:
    if not raw:
        return "free-lite"
    return TIER_SYNONYMS.get(raw.strip().lower(), "free-lite")


def get_tier() -> str:
    """Return the current tier from env, normalized."""
    return normalize_tier(os.getenv("FIRSTTRY_TIER"))


def is_free_tier(tier: Optional[str] = None) -> bool:
    t = tier or get_tier()
    return t in FREE_TIERS


def is_paid_tier(tier: Optional[str] = None) -> bool:
    t = tier or get_tier()
    return t in PAID_TIERS


def _get_license_key_from_env() -> Optional[str]:
    return (
        os.getenv("FIRSTTRY_LICENSE_KEY")
        or os.getenv("FIRSTTRY_LICENSE")
        or os.getenv("FIRSTTRY_PRO_KEY")
    )


def _validate_license_max_security(license_key: str, tier: str) -> None:
    """
    "Max security" = ALWAYS validate + ALWAYS fail closed.

    We keep it defensive, so it won't crash if license_cache is absent,
    but if validation exists and fails → raise.
    """
    try:
        from . import license_cache  # type: ignore
    except Exception:
        # if license_cache isn't there, we still allow free tiers but **not** paid ones
        raise LicenseError(
            f"Tier '{tier}' is locked and license validation backend is missing."
        )

    # common patterns this repo used earlier
    if hasattr(license_cache, "validate_license_key"):
        ok, meta = license_cache.validate_license_key(
            license_key, tier=tier, strict=True
        )
        if not ok:
            raise LicenseError(
                f"License not valid for tier '{tier}'. Please run `firsttry license activate`."
            )
    elif hasattr(license_cache, "validate"):
        ok = license_cache.validate(license_key, tier=tier)
        if not ok:
            raise LicenseError(
                f"License not valid for tier '{tier}'. Please run `firsttry license activate`."
            )
    else:
        # backend is present but unknown interface → fail closed
        raise LicenseError(
            f"Tier '{tier}' requires license. Unknown license backend."
        )


def ensure_license_for_current_tier() -> None:
    tier = get_tier()
    if not is_paid_tier(tier):
        # Free Lite and Free Strict are free forever
        return
    license_key = _get_license_key_from_env()
    if not license_key:
        raise LicenseError(
            f"Tier '{tier}' is locked. Set FIRSTTRY_LICENSE_KEY=... or run `firsttry license activate`."
        )
    _validate_license_max_security(license_key, tier)


# Legacy compatibility functions for existing code
def is_pro() -> bool:
    return get_tier() == "pro"

def is_teams() -> bool:
    return get_tier() == "pro"

def is_developer() -> bool:
    return get_tier() in ("free-lite", "free-strict")