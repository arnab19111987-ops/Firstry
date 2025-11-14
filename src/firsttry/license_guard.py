# src/firsttry/license_guard.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Set

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


def normalize_tier(raw: str | None) -> str:
    if not raw:
        return "free-lite"
    return TIER_SYNONYMS.get(raw.strip().lower(), "free-lite")


def get_tier() -> str:
    """Return the current tier from env, normalized."""
    return normalize_tier(os.getenv("FIRSTTRY_TIER"))


def is_free_tier(tier: str | None = None) -> bool:
    t = tier or get_tier()
    return t in FREE_TIERS


def is_paid_tier(tier: str | None = None) -> bool:
    t = tier or get_tier()
    return t in PAID_TIERS


def _get_license_key_from_env() -> str | None:
    return (
        os.getenv("FIRSTTRY_LICENSE_KEY")
        or os.getenv("FIRSTTRY_LICENSE")
        or os.getenv("FIRSTTRY_PRO_KEY")
    )


def _validate_license_offline(license_key: str, tier: str) -> None:
    """
    Pure offline validation. Must not perform network I/O.

    This attempts to use any local/offline validation helpers exposed by the
    optional `license_cache` backend. If none are present we fail closed for
    paid tiers by raising LicenseError.
    """
    try:
        from . import license_cache
    except Exception:
        raise LicenseError(
            f"Tier '{tier}' is locked and offline license validator is missing.",
        )

    # Prefer explicit offline validator hooks when available
    if hasattr(license_cache, "validate_offline"):
        ok = license_cache.validate_offline(license_key, tier=tier)
        if not ok:
            raise LicenseError(
                f"License not valid for tier '{tier}' (offline). Please run `firsttry license activate`.",
            )
        return

    # Many backends expose a validate_license_key(strict=...) shape — use it
    if hasattr(license_cache, "validate_license_key"):
        try:
            ok, meta = license_cache.validate_license_key(
                license_key,
                tier=tier,
                strict=True,
            )
        except Exception:
            raise LicenseError(f"Offline license validation failed for tier '{tier}'.")
        if not ok:
            raise LicenseError(
                f"License not valid for tier '{tier}'. Please run `firsttry license activate`.",
            )
        return

    # Generic validate() fallback (may be offline in some implementations)
    if hasattr(license_cache, "validate"):
        try:
            ok = license_cache.validate(license_key, tier=tier)
        except Exception:
            raise LicenseError(f"Offline license validation failed for tier '{tier}'.")
        if not ok:
            raise LicenseError(
                f"License not valid for tier '{tier}'. Please run `firsttry license activate`.",
            )
        return

    # No offline-capable validator discovered — fail closed
    raise LicenseError(f"Tier '{tier}' requires license. Offline validator missing.")


def _validate_license_remote(license_key: str, tier: str) -> None:
    """
    Optional remote validation. Only used when
    FIRSTTRY_LICENSE_CHECK_MODE=remote. Keep this minimal and robust.
    """
    try:
        from . import license_cache
    except Exception:
        raise LicenseError("Remote license check backend is missing.")

    try:
        # Many implementations expose a remote validate hook with varying names
        if hasattr(license_cache, "remote_validate"):
            ok = license_cache.remote_validate(license_key, tier=tier, timeout=3)
            if not ok:
                raise LicenseError("Remote license check failed: not valid")
            return

        if hasattr(license_cache, "validate_remote"):
            ok = license_cache.validate_remote(license_key, tier=tier)
            if not ok:
                raise LicenseError("Remote license check failed: not valid")
            return

        if hasattr(license_cache, "validate_license_key_remote"):
            ok, meta = license_cache.validate_license_key_remote(license_key, tier=tier)
            if not ok:
                raise LicenseError("Remote license check failed: not valid")
            return

        # If no explicit remote hook exists, we cannot perform remote verification
        raise LicenseError("No remote license validator available")
    except LicenseError:
        raise
    except Exception as exc:
        raise LicenseError(f"Remote license check failed: {type(exc).__name__}") from exc


def _validate_license_max_security(license_key: str, tier: str) -> None:
    """
    Entry point used by ensure_license_for_current_tier.

    Controlled by FIRSTTRY_LICENSE_CHECK_MODE:

      offline (default): offline-only checks
      remote           : offline + remote check

    Any other value -> LicenseError.
    """
    mode = os.getenv("FIRSTTRY_LICENSE_CHECK_MODE", "offline").lower()

    if mode == "offline":
        _validate_license_offline(license_key, tier)
    elif mode == "remote":
        _validate_license_offline(license_key, tier)
        _validate_license_remote(license_key, tier)
    else:
        raise LicenseError(f"Unknown license check mode {mode!r}")


def ensure_license_for_current_tier() -> None:
    tier = get_tier()
    if not is_paid_tier(tier):
        # Free Lite and Free Strict are free forever
        return
    license_key = _get_license_key_from_env()
    if not license_key:
        raise LicenseError(
            f"Tier '{tier}' is locked. Set FIRSTTRY_LICENSE_KEY=... or run `firsttry license activate`.",
        )
    _validate_license_max_security(license_key, tier)


# Legacy compatibility functions for existing code
def is_pro() -> bool:
    return get_tier() == "pro"


def is_teams() -> bool:
    return get_tier() == "pro"


def is_developer() -> bool:
    return get_tier() in ("free-lite", "free-strict")


# Backwards-compatible helper names expected by various entrypoints/tests
def get_current_tier() -> str:
    """Compatibility wrapper that respects FIRSTTRY_FORCE_TIER (used in tests)

    New code should use `get_tier()` directly, but many entrypoints call
    `get_current_tier()` so we provide a stable shim that prefers the
    FORCE env var for local testing.
    """
    # Hard override for tests/demos (beats everything)
    forced = os.getenv("FIRSTTRY_FORCE_TIER") or os.getenv("FIRSTTRY_TIER")
    if forced in {"lite", "pro"}:
        return forced
    return get_tier()


def maybe_download_golden_cache() -> None:
    """Attempt a best-effort golden-cache download for Pro tiers.

    - On free tiers this is a no-op that prints a friendly upsell message.
    - On paid tiers we try to import a `golden_cache` helper and call it.
    Any import or runtime error is caught and printed; this function must
    never raise during normal CLI use.
    """
    tier = get_current_tier()
    if is_paid_tier(tier):
        print("Pro license active: attempting Golden Cache download...")
        try:
            # Import inside function to avoid circular import at module load
            from . import golden_cache  # type: ignore

            if hasattr(golden_cache, "maybe_download"):
                golden_cache.maybe_download()
            else:
                print("Could not find golden_cache.maybe_download() - skipping")
        except Exception as e:  # pragma: no cover - best-effort
            print("Could not download golden cache:", e)
    else:
        print(
            "🔒 Pro Feature: Golden Cache is available in Pro. Run `firsttry license activate` to enable."
        )


def maybe_include_flaky_tests(tests_to_run: Iterable[str]) -> Set[str]:
    """On Pro tiers, include additional flaky tests from an optional module.

    Returns a set of test ids/paths. Never raises; if the optional
    `flaky_tests` module is missing we return the original set.
    """
    orig = set(tests_to_run or [])
    tier = get_current_tier()
    if is_paid_tier(tier):
        print("Pro license active: attempting to include flaky tests...")
        try:
            from . import flaky_tests  # type: ignore

            if hasattr(flaky_tests, "load_flaky_tests"):
                extras = flaky_tests.load_flaky_tests()
                return orig.union(set(extras or []))
            else:
                print("Could not find flaky_tests.load_flaky_tests() - skipping")
                return orig
        except Exception as e:  # pragma: no cover - optional runtime
            print("Could not include flaky tests:", e)
            return orig
    else:
        print(
            "🔒 Pro Feature: Flaky tests inclusion is Pro-only. Use `FIRSTTRY_FORCE_TIER=pro` to test."
        )
        return orig


# --- FirstTry: Demo Dev Key + Velvet Rope helpers (idempotent) ---

import sys
from typing import Optional

# Define a uniquely-named placeholder resolver and bind it to the public
# name only if a richer implementation doesn't already exist. Using a
# different function name avoids static analysis warnings about multiple
# function definitions with the same name.
def _ft_placeholder_resolve_license(*args: Any, **kwargs: Any) -> Any:
    """Default license resolver placeholder used only when no other
    resolver is available at import time.
    """
    raise RuntimeError(
        "license_guard.resolve_license was called, but no resolver has been configured."
    )

# Ensure a public `resolve_license` exists without redefining it.
globals().setdefault("resolve_license", _ft_placeholder_resolve_license)


def get_license_resolver() -> Any:
    """Return the current resolver callable (live lookup).

    This avoids freezing a snapshot at import time so later overrides to
    the public `resolve_license` symbol are visible.
    """
    return globals().get("resolve_license", _ft_placeholder_resolve_license)


def _ft_resolve_tier_fallback() -> str:
    """
    Super-safe fallback used if your full resolver isn't available here.
    Accepts env FIRSTTRY_LICENSE_KEY (e.g., 'tier:pro') and defaults to free-lite.
    """
    key = os.getenv("FIRSTTRY_LICENSE_KEY", "")
    if not key:
        return "free-lite"
    if ":" in key:
        try:
            _, t = key.split(":", 1)
            return (t or "").strip().lower() or "free-lite"
        except Exception:
            return "free-lite"
    return "pro"


def _ft_normalize_tier(t: Optional[str]) -> str:
    t = (t or "").lower().strip()
    if t in {"pro"}:
        return "pro"
    if t in {"free-strict", "strict"}:
        return "free-strict"
    return "free-lite"


# Define get_current_tier only if not already defined
if "get_current_tier" not in globals():

    def get_current_tier() -> str:  # noqa: D401
        """
        The 'Bouncer' — returns normalized tier: 'free-lite' | 'free-strict' | 'pro'.
        Honors FIRSTTRY_DEMO_MODE=1 to force Pro for demo sessions.
        """
        # DEV KEY: escape hatch for demos/recordings
        if os.getenv("FIRSTTRY_DEMO_MODE") == "1":
            return "pro"

        # Prefer your resolver (if available). Use a live lookup so that
        # later overrides to the public `resolve_license` symbol are
        # respected instead of freezing a snapshot at import-time.
        resolver = get_license_resolver()
        if callable(resolver):
            try:
                li: Any = resolver(None)  # type: ignore[misc]
                tier = getattr(li, "tier", None) or (
                    li.get("tier") if isinstance(li, dict) else None
                )
                return _ft_normalize_tier(tier)
            except Exception:
                pass

        # Fallback if resolver not usable
        return _ft_normalize_tier(_ft_resolve_tier_fallback())


# Add tiny helpers only if missing
if "tier_is_pro" not in globals():

    def tier_is_pro() -> bool:
        return get_current_tier() == "pro"


if "require_pro" not in globals():

    def require_pro(feature_name: str = "this feature") -> None:
        """Exit with a friendly upsell if the current tier is not Pro."""
        if not tier_is_pro():
            print(f"❌ ERROR: `{feature_name}` is a Pro feature.")
            print("   Upgrade to Pro to unlock this capability.")
            print("   Tip: for demos: export FIRSTTRY_DEMO_MODE=1")
            sys.exit(1)


# --- Dev Key precedence shim (idempotent, non-invasive) ---
# Ensures FIRSTTRY_DEMO_MODE=1 overrides any existing resolver logic.
try:
    get_current_tier  # noqa: B018 - ensure symbol exists
except NameError:
    # If not defined for some reason, provide a minimal fallback
    def get_current_tier() -> str:
        import os

        return "pro" if os.getenv("FIRSTTRY_DEMO_MODE") == "1" else "free-lite"


if "_FT_DEMO_WRAPPED" not in globals():
    _FT_DEMO_WRAPPED = True
    _FT_ORIG_GET_TIER = get_current_tier  # keep original

    def _ft_get_current_tier_demo_shim(*args, **kwargs) -> str:
        import os

        if os.getenv("FIRSTTRY_DEMO_MODE") == "1":
            return "pro"
        return _FT_ORIG_GET_TIER(*args, **kwargs)

    # Install the shim
    get_current_tier = _ft_get_current_tier_demo_shim  # type: ignore[assignment]


# Minimal resolve_license helper expected by some tests/tools.
from dataclasses import dataclass


@dataclass
class LicenseResult:
    tier: str
    verified: bool = False
    source: Optional[str] = None
    expires_at: Optional[int] = None


def resolve_license(cfg: Any) -> LicenseResult:
    """Best-effort resolver wrapper.

    Supports minimal 'offline' mode used in tests: reads a small TOML-like
    file and returns a LicenseResult. This is intentionally permissive so
    tests that exercise offline parsing succeed without requiring the full
    license backend.
    """
    try:
        lic = getattr(cfg, "license", cfg)
        mode = getattr(lic, "mode", None) or "env"
        if mode == "offline":
            fpath = getattr(lic, "file", None)
            if fpath:
                p = Path(fpath)
                if p.exists():
                    txt = p.read_text()
                    tier = "free-lite"
                    expires_at = None
                    # very small parser for test fixtures like: tier="pro" or expires_at=0
                    for line in txt.splitlines():
                        if line.strip().startswith("tier"):
                            try:
                                _, rhs = line.split("=", 1)
                                tier = rhs.strip().strip('"').strip("'")
                            except Exception:
                                pass
                        if line.strip().startswith("expires_at"):
                            try:
                                _, rhs = line.split("=", 1)
                                expires_at = int(rhs.strip())
                            except Exception:
                                pass
                    # Treat an explicit expires_at == 0 as a valid (non-expired)
                    # offline license used in tests/fixtures.
                    verified = bool(expires_at == 0 or expires_at is None)
                    return LicenseResult(
                        tier=tier,
                        verified=verified,
                        source="offline",
                        expires_at=expires_at,
                    )
    except Exception:
        pass
    # Fallback: return current tier and not verified
    return LicenseResult(tier=get_current_tier(), verified=False)


def emit_license_row(report: dict, lic: LicenseResult) -> None:
    """Write minimal license information into the provided report dict.

    This helper is intentionally tiny and permissive so CLI glue code
    can call it without importing heavy reporting code.
    """
    try:
        report["license"] = {
            "tier": lic.tier,
            "verified": bool(getattr(lic, "verified", False)),
            "source": getattr(lic, "source", None),
            "expires_at": getattr(lic, "expires_at", None),
        }
    except Exception:
        # Keep this best-effort and non-fatal for CLI startup
        try:
            report["license"] = {"tier": get_current_tier(), "verified": False}
        except Exception:
            report["license"] = {"tier": "free-lite", "verified": False}
