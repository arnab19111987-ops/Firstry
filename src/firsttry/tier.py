from __future__ import annotations

from typing import Callable
import os

from . import license_guard


def _normalize_to_simple(t: str | None) -> str:
    """Map existing license_guard tier strings to simple canonical tiers:
    'free', 'pro', 'enterprise'.
    """
    if not t:
        return "free"
    s = str(t).lower()
    if s.startswith("pro"):
        return "pro"
    if s.startswith("promax") or s.startswith("enterprise") or s == "org":
        return "enterprise"
    # free-strict / free-lite / free / dev -> free
    return "free"


def get_current_tier() -> str:
    """Return one of: 'free', 'pro', 'enterprise'. Delegates to license_guard.

    This function intentionally does not change any underlying license
    behavior; it only normalizes the various internal tier strings to a
    compact public set the CLI and gating helpers can use.
    """
    try:
        raw = license_guard.get_current_tier()
    except Exception:
        # Fall back to environment variable (tests may set FIRSTTRY_TIER)
        raw = os.getenv("FIRSTTRY_TIER")
    return _normalize_to_simple(raw)


def tier_allowed(current_tier: str | None, min_tier: str) -> bool:
    """Return True if current_tier >= min_tier.

    min_tier is one of 'free', 'pro', 'enterprise'. If current_tier is None,
    use get_current_tier() to resolve.
    """
    order = {"free": 0, "pro": 1, "enterprise": 2}
    cur = current_tier or get_current_tier()
    cur_norm = _normalize_to_simple(cur)
    min_norm = _normalize_to_simple(min_tier)
    return order[cur_norm] >= order[min_norm]


def require_tier(min_tier: str) -> Callable:
    """Decorator requiring at least `min_tier`.

    On failure prints a short message and exits with code 2.
    """

    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Import via sys.modules each call to ensure tests that monkeypatch
            # `firsttry.tier.get_current_tier` are respected even if module
            # objects were reloaded or mutated elsewhere in the test-suite.
            import importlib

            cur = importlib.import_module(__name__).get_current_tier()
            if not tier_allowed(cur, min_tier):
                print(f"This feature requires a {min_tier.capitalize()} license (current tier: {cur}).")
                raise SystemExit(2)
            return fn(*args, **kwargs)

        wrapper.__name__ = getattr(fn, "__name__", "wrapped")
        wrapper.__doc__ = fn.__doc__
        return wrapper

    return decorator
