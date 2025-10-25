from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple
import json
import os
import urllib.request

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


def load_cache() -> Optional[CachedLicense]:
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
            }
        ),
        encoding="utf-8",
    )


def is_fresh(c: CachedLicense) -> bool:
    return _now() - c.ts <= FRESH_FOR


def remote_verify(base_url: str, product: str, key: str) -> Tuple[bool, list[str]]:
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


def assert_license(product: str = "firsttry") -> Tuple[bool, list[str], str]:
    """
    Returns (ok, features, reason). Uses cache if fresh; otherwise re-verifies.
    Config:
      FIRSTTRY_LICENSE_KEY=<key>
      FIRSTTRY_LICENSE_URL=<http://host:port>
    """
    key = os.getenv("FIRSTTRY_LICENSE_KEY", "").strip()
    url = os.getenv("FIRSTTRY_LICENSE_URL", "").strip()
    if not key or not url:
        return False, [], "missing FIRSTTRY_LICENSE_KEY or FIRSTTRY_LICENSE_URL"

    c = load_cache()
    if c and c.key == key and is_fresh(c):
        return c.valid, c.features, "cache"

    # Import module at call time so test monkeypatches of
    # firsttry.license_cache.remote_verify are reliably picked up.
    from firsttry import license_cache as _lc

    ok, feats = _lc.remote_verify(url, product, key)
    save_cache(CachedLicense(key=key, valid=ok, features=feats, ts=_now()))
    return ok, feats, "remote"
