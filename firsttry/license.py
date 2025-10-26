# firsttry/license.py
from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Any, Dict, Tuple
import base64
import hashlib
import hmac
from pathlib import Path


class HTTPResponseLike(Protocol):
    """Protocol for HTTP response objects."""

    def json(self) -> dict:
        ...


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


# -----------------------------
# HMAC signing + Pro gating
# -----------------------------

# For dev/tests only. In production load from env/secret store.
DEFAULT_SHARED_SECRET = "dev-secret-change-me"


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
