# firsttry/license.py
from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Any, Dict, Tuple
from datetime import datetime, timezone, timedelta
import base64
import hashlib
import hmac
from pathlib import Path


class HTTPResponseLike(Protocol):
    """Protocol for HTTP response objects."""

    def json(self) -> dict: ...


@dataclass
class LicenseInfo:
    valid: bool
    plan: str
    expiry: Optional[str]
    raw: dict


CACHE_PATH = pathlib.Path.home() / ".firsttry" / "license.json"


def _ensure_cache_parent():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_cached_license() -> Optional[LicenseInfo]:
    if not CACHE_PATH.exists():
        return None
    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return LicenseInfo(
        valid=bool(data.get("valid")),
        plan=str(data.get("plan", "")),
        expiry=data.get("expiry"),
        raw=data,
    )


def save_cached_license(info: LicenseInfo) -> None:
    _ensure_cache_parent()
    CACHE_PATH.write_text(
        json.dumps(info.raw, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def verify_with_server(
    license_key: str,
    server_url: str,
    http_post: Callable[..., HTTPResponseLike],
) -> LicenseInfo:
    """
    server_url: e.g. http://localhost:8000/api/v1/license/verify
    http_post: injected callable so we can mock in tests.

    Expected server response JSON:
    { "valid": true, "plan": "pro", "expiry": "2026-01-01T00:00:00Z" }
    """
    resp = http_post(
        server_url,
        json={"license_key": license_key},
        timeout=5,
    )
    data = resp.json()

    info = LicenseInfo(
        valid=bool(data.get("valid")),
        plan=str(data.get("plan", "")),
        expiry=data.get("expiry"),
        raw=data,
    )
    return info


def verify_license(
    license_key: Optional[str],
    server_url: Optional[str],
    http_post: Optional[Callable[..., HTTPResponseLike]] = None,
) -> LicenseInfo:
    """
    Public helper.
    - Pulls key from env if not provided.
    - Falls back to cached info if server_url missing.
    - Saves cache on success.
    """
    if license_key is None:
        license_key = os.getenv("FIRSTTRY_LICENSE_KEY")

    if not license_key:
        # no key at all -> treat as invalid free tier
        return LicenseInfo(
            valid=False, plan="free", expiry=None, raw={"valid": False, "plan": "free"}
        )

    if server_url and http_post:
        info = verify_with_server(license_key, server_url, http_post)
        save_cached_license(info)
        return info

    cached = load_cached_license()
    if cached:
        return cached

    # Last resort, assume free
    return LicenseInfo(
        valid=False, plan="free", expiry=None, raw={"valid": False, "plan": "free"}
    )


def license_summary_for_humans(lic_obj) -> str:
    """
    Produce a compact human-friendly one-line summary for the given license object.

    Accepts either a mapping (dict-like) or an object with attributes. The function
    adapts common field names (`plan` / `tier`, `expiry` / `expires_at`, `valid` / `is_valid`).
    Expiry strings in ISO format (including a trailing 'Z') are handled.
    """

    def _get(o, k):
        try:
            if isinstance(o, dict):
                return o.get(k)
            return getattr(o, k, None)
        except Exception:
            return None

    plan = _get(lic_obj, "plan") or _get(lic_obj, "tier") or "trial"
    expires_raw = (
        _get(lic_obj, "expires_at")
        or _get(lic_obj, "expiry")
        or _get(lic_obj, "expiry_date")
    )
    is_valid = _get(lic_obj, "is_valid")
    if is_valid is None:
        is_valid = _get(lic_obj, "valid")
    if is_valid is None:
        is_valid = True

    expires_dt = None
    if isinstance(expires_raw, str):
        try:
            # handle trailing Z (UTC) which fromisoformat doesn't accept
            iso = expires_raw
            if iso.endswith("Z"):
                iso = iso[:-1] + "+00:00"
            expires_dt = datetime.fromisoformat(iso)
        except Exception:
            expires_dt = None
    elif isinstance(expires_raw, datetime):
        expires_dt = expires_raw

    days_remaining_txt = ""
    if expires_dt is not None:
        now = datetime.now(timezone.utc)
        # normalize naive datetimes to UTC
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        remaining_days = (expires_dt - now).days
        days_remaining_txt = (
            f" ({remaining_days} day(s) left)" if remaining_days >= 0 else " (expired)"
        )

    status = "valid" if bool(is_valid) else "invalid"
    return f"License: {plan}{days_remaining_txt} • Status: {status}"


def ensure_trial_license_if_missing(days: int = 3, plan: str = "trial") -> LicenseInfo:
    """
    Ensure a trial license is present in the cache. If a cached license exists, return it.
    Otherwise create a short-lived trial license (signed) and save it to the cache,
    returning the resulting LicenseInfo.
    """
    cached = load_cached_license()
    if cached:
        return cached

    expiry_dt = datetime.now(timezone.utc) + timedelta(days=days)
    # represent expiry in ISO 8601 with Z for UTC to be compatible with callers
    expiry_iso = expiry_dt.isoformat().replace("+00:00", "Z")

    payload = build_license_payload(valid=True, plan=plan, expiry=expiry_iso)
    info = LicenseInfo(valid=True, plan=plan, expiry=expiry_iso, raw=payload)
    try:
        save_cached_license(info)
    except Exception:
        # best-effort: ignore write errors and still return the info object
        pass
    return info


# -----------------------------
# HMAC signing + Pro gating
# -----------------------------

# For dev/tests only. In production load from env/secret store.
# Prefer reading from environment so secrets aren't hardcoded in source.
DEFAULT_SHARED_SECRET = os.getenv("FIRSTTRY_SHARED_SECRET", "dev-secret-change-me")


def _license_cache_path() -> Path:
    return Path.home() / ".firsttry" / "license.json"


def _sign_payload(
    valid: bool, plan: Optional[str], expiry: Optional[str], secret: str
) -> str:
    msg = f"{valid}|{plan}|{expiry}"
    mac = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")


def verify_sig(payload: Dict[str, Any], secret: str = DEFAULT_SHARED_SECRET) -> bool:
    expected = _sign_payload(
        bool(payload.get("valid", False)),
        payload.get("plan"),
        payload.get("expiry"),
        secret,
    )
    got = payload.get("sig", "")
    return hmac.compare_digest(expected, got)


def build_license_payload(
    valid: bool,
    plan: Optional[str],
    expiry: Optional[str],
    secret: str = DEFAULT_SHARED_SECRET,
) -> Dict[str, Any]:
    payload = {"valid": valid, "plan": plan, "expiry": expiry}
    payload["sig"] = _sign_payload(valid, plan, expiry, secret)
    return payload


def require_license() -> Tuple[Dict[str, Any], None]:
    """
    Strict Pro gating: allow only signed, valid cached licenses.

    Behavior:
    - If no cached payload: block with exit 3.
    - If payload lacks HMAC signature or signature invalid: block.
    - If payload present, signature valid, and valid==True: allow.
    """
    lic_obj = load_cached_license()
    lic_payload: Optional[Dict[str, Any]]
    if isinstance(lic_obj, LicenseInfo):
        lic_payload = {
            "valid": lic_obj.valid,
            "plan": lic_obj.plan,
            "expiry": lic_obj.expiry,
        }
    else:
        lic_payload = lic_obj  # may be dict or None

    if not lic_payload:
        print("FirstTry Pro feature. Run `firsttry license buy` to upgrade.")
        raise SystemExit(3)

    # Must have a signature and pass verification
    if (
        "sig" not in lic_payload
        or not verify_sig(lic_payload)
        or not lic_payload.get("valid")
    ):
        print("License invalid or tampered. Run `firsttry license buy` to upgrade.")
        raise SystemExit(3)

    return lic_payload, None
