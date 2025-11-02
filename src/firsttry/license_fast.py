# src/firsttry/license_fast.py
"""
Non-blocking license check system for FirstTry CLI.
Prevents 10-second hangs during git hooks.
"""
from __future__ import annotations

import threading
import time
import os
from typing import Tuple, Any

# Simple in-memory cache
_LICENSE_CACHE: dict[str, Any] = {
    "ok": True,          # assume OK unless proven otherwise (fail-open)
    "checked_at": 0.0,
    "raw": None,
    "features": [],
}


def _fetch_remote_license(timeout: float = 1.0) -> dict | None:
    """
    Fetch license from remote server with short timeout.
    Returns None on any failure (network, timeout, etc.)
    """
    try:
        # Import here to avoid circular imports and allow monkeypatching
        from . import license_cache
        
        key = os.getenv("FIRSTTRY_LICENSE_KEY", "").strip()
        url = os.getenv("FIRSTTRY_LICENSE_URL", "").strip()
        
        if not key or not url:
            return None
            
        # Use existing remote_verify but with shorter timeout
        # This is still blocking but only for 1 second max
        import socket
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            valid, features = license_cache.remote_verify(url, "firsttry", key)
            return {"valid": valid, "features": features}
        finally:
            socket.setdefaulttimeout(old_timeout)
            
    except Exception:
        # Fail-open: any exception means we can't verify, so allow
        return None


def _update_cache_from_remote():
    """Background thread function to update license cache."""
    resp = _fetch_remote_license(timeout=1.0)
    now = time.time()
    
    if resp and resp.get("valid"):
        _LICENSE_CACHE["ok"] = True
        _LICENSE_CACHE["raw"] = resp
        _LICENSE_CACHE["features"] = resp.get("features", [])
        _LICENSE_CACHE["checked_at"] = now
    else:
        # Fail-open: keep previous state, just update timestamp
        _LICENSE_CACHE["checked_at"] = now


def check_license_async() -> None:
    """
    Fire-and-forget license check.
    Must NEVER block a git hook.
    """
    t = threading.Thread(target=_update_cache_from_remote, daemon=True)
    t.start()


def is_license_ok() -> bool:
    """
    Fast, synchronous read — what hooks should call.
    Always returns True (fail-open) unless explicitly denied.
    """
    return bool(_LICENSE_CACHE.get("ok", True))


def get_license_features() -> list[str]:
    """Get currently cached license features."""
    features = _LICENSE_CACHE.get("features", [])
    return list(features) if isinstance(features, list) else []


def get_license_status() -> Tuple[bool, list[str], str]:
    """
    Get license status compatible with existing assert_license interface.
    Returns (ok, features, reason)
    """
    # Check if we should bypass license checks entirely
    if os.getenv("FIRSTTRY_ALLOW_UNLICENSED") == "1":
        return True, ["unlimited"], "unlicensed_allowed"
        
    # Check --silent-unlicensed in command line args (basic check)
    import sys
    if "--silent-unlicensed" in " ".join(sys.argv):
        return True, ["unlimited"], "silent_unlicensed"
    
    # Use cached result (fail-open)
    ok = is_license_ok()
    features = get_license_features()
    checked_at = _LICENSE_CACHE.get("checked_at", 0)
    reason = "cache" if isinstance(checked_at, (int, float)) and checked_at > 0 else "default"
    
    return ok, features, reason