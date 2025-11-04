from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def repo_license_path() -> Path:
    return Path.cwd() / ".firsttry" / "license.key"


def user_license_path() -> Path:
    # Use XDG-friendly config location (~/.config/firsttry/license.key)
    return Path(os.path.expanduser("~")) / ".config" / "firsttry" / "license.key"


def load_license_key() -> Optional[str]:
    """Return the license key from FIRSTTRY_LICENSE_KEY (env), repo, or user cache.

    Precedence: env -> repo -> user
    """
    key = os.getenv("FIRSTTRY_LICENSE_KEY")
    if key and key.strip():
        return key.strip()

    rp = repo_license_path()
    try:
        if rp.exists():
            return rp.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    up = user_license_path()
    try:
        if up.exists():
            return up.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    return None


def save_license_key(key: str, scope: str = "user") -> None:
    """Persist the license key. scope in ('user', 'repo')."""
    key = key.strip()
    if not key:
        raise ValueError("empty license key")

    if scope == "repo":
        p = repo_license_path()
    else:
        p = user_license_path()

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(key, encoding="utf-8")


def remove_license_key(scope: str = "all") -> None:
    if scope in ("repo", "all"):
        rp = repo_license_path()
        try:
            if rp.exists():
                rp.unlink()
        except Exception:
            pass

    if scope in ("user", "all"):
        up = user_license_path()
        try:
            if up.exists():
                up.unlink()
        except Exception:
            pass


__all__ = [
    "load_license_key",
    "save_license_key",
    "remove_license_key",
    "repo_license_path",
    "user_license_path",
]
