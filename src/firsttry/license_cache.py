from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Root-level forwarder/implementation to ensure a single, canonical
# firsttry.license_cache module is imported by tests and runtime.

CACHE_PATH = Path(os.path.expanduser("~")) / ".firsttry" / "license.json"
FRESH_FOR = timedelta(days=7)


@dataclass(frozen=True)
class CachedLicense:
    key: str
    valid: bool
    features: list[str]
    ts: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_cache() -> CachedLicense | None:
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["ts"])
        return CachedLicense(
            key=data["key"],
            valid=bool(data["valid"]),
            features=list(data.get("features", [])),
            ts=ts,
        )
    except Exception:
        return None


def save_cache(c: CachedLicense) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(
            {
                "key": c.key,
                "valid": c.valid,
                "features": c.features,
                "ts": c.ts.isoformat(),
            },
        ),
        encoding="utf-8",
    )


def is_fresh(c: CachedLicense) -> bool:
    return _now() - c.ts <= FRESH_FOR


def remote_verify(base_url: str, product: str, key: str) -> tuple[bool, list[str]]:
    payload = json.dumps({"product": product, "key": key}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/license/verify",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        js = json.loads(resp.read().decode("utf-8"))
    return bool(js.get("valid")), list(js.get("features", []))


def assert_license(product: str = "firsttry") -> tuple[bool, list[str], str]:
    """Returns (ok, features, reason). Uses cache if fresh; otherwise re-verifies.
    Config:
      FIRSTTRY_LICENSE_KEY=<key>
      FIRSTTRY_LICENSE_URL=<http://host:port>
      FIRSTTRY_LICENSE_BACKEND=env  (use ENV backend)
      FIRSTTRY_LICENSE_ALLOW=<tier> (ENV backend: allowed tier)
    """
    # If a remote URL is explicitly configured prefer remote verification.
    # This allows tests (and users) to force remote-checking by setting
    # FIRSTTRY_LICENSE_URL even when a default ENV backend is present.
    key = os.getenv("FIRSTTRY_LICENSE_KEY", "").strip()
    url = os.getenv("FIRSTTRY_LICENSE_URL", "").strip()
    if key and url:
        # If a fresh cache exists for this key, use it to avoid unnecessary
        # network calls. Otherwise perform a remote verify and save the
        # result to cache for subsequent calls.
        c = load_cache()
        if c and c.key == key and is_fresh(c):
            return c.valid, c.features, "cache"
        try:
            # Resolve remote_verify at call time so pytest monkeypatching
            # of firsttry.license_cache.remote_verify is respected.
            rv = getattr(sys.modules[__name__], "remote_verify")
            ok, feats = rv(url, product, key)
            feats_list = list(feats) if isinstance(feats, (list, tuple)) else [str(feats)]
            save_cache(CachedLicense(key=key, valid=ok, features=feats_list, ts=_now()))
            return ok, feats_list, "remote"
        except Exception:
            # Remote failed; check cache as a fallback
            c = load_cache()
            if c and c.key == key and is_fresh(c):
                return c.valid, c.features, "cache"
            raise

    # Check if ENV backend is requested (only used when no explicit URL provided)
    backend = os.getenv("FIRSTTRY_LICENSE_BACKEND", "").strip().lower()
    if backend == "env":
        # ENV backend: validate using FIRSTTRY_LICENSE_ALLOW
        if not key:
            return False, [], "missing FIRSTTRY_LICENSE_KEY"
        allowed = os.getenv("FIRSTTRY_LICENSE_ALLOW", "").strip().lower()
        if not allowed:
            return False, [], "ENV backend requires FIRSTTRY_LICENSE_ALLOW"
        # ENV backend always validates as OK if key and allowed tier are set
        return True, [allowed], "env"

    # Default: no usable backend configured
    if not key or not url:
        return False, [], "missing FIRSTTRY_LICENSE_KEY or FIRSTTRY_LICENSE_URL"

    # Prefer remote verification when a URL is configured. If the remote
    # call fails for any reason, fall back to cache so tests that stub the
    # network can still exercise caching behavior.
    # (Unreachable) kept for clarity
    return False, [], "missing FIRSTTRY_LICENSE_KEY or FIRSTTRY_LICENSE_URL"


def validate_license_key(key: str, tier: str = "", strict: bool = True) -> tuple[bool, dict]:
    """Validate a license key for a specific tier.
    Returns (ok, metadata) tuple.
    Used by license_guard._validate_license_max_security().
    """
    backend = os.getenv("FIRSTTRY_LICENSE_BACKEND", "").strip().lower()
    if backend == "env":
        # ENV backend: check if tier is in allowed list
        allowed = os.getenv("FIRSTTRY_LICENSE_ALLOW", "").strip().lower()
        if not allowed:
            return False, {"reason": "ENV backend requires FIRSTTRY_LICENSE_ALLOW"}
        # Normalize tier names for comparison
        allowed_tiers = [t.strip() for t in allowed.split(",")]
        # Check if requested tier is allowed
        if tier.lower() in allowed_tiers or "pro" in allowed_tiers:
            return True, {"backend": "env", "tier": tier, "allowed": allowed_tiers}
        return False, {"reason": f"Tier '{tier}' not in FIRSTTRY_LICENSE_ALLOW={allowed}"}

    # Default: use assert_license
    ok, features, reason = assert_license()
    return ok, {"features": features, "reason": reason}


def clear_cache() -> None:
    """Remove any on-disk license cache.

    This is intentionally tiny and safe for tests. It helps avoid
    order-dependent test failures when other tests create the
    ~/.firsttry/license.json cache file.
    """
    try:
        if CACHE_PATH.exists():
            CACHE_PATH.unlink()
    except Exception:
        # Best-effort silent failure; tests shouldn't crash if removal fails.
        pass
