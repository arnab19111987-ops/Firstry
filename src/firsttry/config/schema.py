from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError


class LicenseCfg(BaseModel):
    mode: str = Field(default="env", description="env|offline|jwt")
    file: Optional[str] = None
    grace_days: int = 0

class RemoteCfg(BaseModel):
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None
    region: Optional[str] = None
    require_kms: bool = False
    allow_buckets: list[str] = []

class PolicyCfg(BaseModel):
    no_network: bool = False
    fips_strict: bool = False
    privacy_min: bool = False
    retention_days: int = 30

class AppCfg(BaseModel):
    license: LicenseCfg = LicenseCfg()
    remote: RemoteCfg = RemoteCfg()
    policy: PolicyCfg = PolicyCfg()

def _load_toml(path: Path) -> dict:
    try:
        import tomllib
        if path.exists():
            return tomllib.loads(path.read_text())
    except Exception:
        pass
    return {}

def load_config(cli_overrides: dict | Path | None = None) -> AppCfg:
    """Precedence: CLI > env > ./firsttry.toml > ~/.config/firsttry/config.toml

    Accepts either a dict of overrides (as before) or a Path. If a Path is
    provided it acts as the working directory to resolve a local `firsttry.toml`
    (useful for tests that pass a Path). None behaves as before.
    """
    # If a Path was passed, treat it as the working directory for local loading
    cwd: Path | None = None
    if isinstance(cli_overrides, Path):
        cwd = cli_overrides if cli_overrides.is_dir() else cli_overrides.parent

    home = Path(os.path.expanduser("~"))
    merged: dict = {}
    # global
    merged |= _load_toml(home/".config/firsttry/config.toml")
    # local
    merged |= _load_toml((cwd or Path.cwd())/"firsttry.toml")
    # env
    env = {
        "policy": {
            "no_network": os.getenv("FIRSTTRY_NO_NETWORK") == "1",
            "fips_strict": os.getenv("FIRSTTRY_FIPS_STRICT") == "1",
            "privacy_min": os.getenv("FIRSTTRY_PRIVACY_MIN") == "1",
        },
        "license": {
            "mode": os.getenv("FIRSTTRY_LICENSE_MODE") or None,
            "file": os.getenv("FIRSTTRY_LICENSE_FILE") or None,
            "grace_days": int(os.getenv("FIRSTTRY_LICENSE_GRACE_DAYS") or 0),
        },
        "remote": {
            "s3_bucket": os.getenv("FIRSTTRY_S3_BUCKET") or None,
            "s3_prefix": os.getenv("FIRSTTRY_S3_PREFIX") or None,
            "region": os.getenv("FIRSTTRY_AWS_REGION") or None,
            "require_kms": os.getenv("FIRSTTRY_REQUIRE_KMS") == "1",
        },
    }
    # overlay non-None env
    for k, v in env.items():
        merged.setdefault(k, {})
        for kk, vv in v.items():
            if vv is not None:
                merged[k][kk] = vv
    # CLI
    # If cli_overrides is a mapping overlay it. If it was a Path we already
    # handled the cwd case above and there are no overrides to apply.
    if isinstance(cli_overrides, dict):
        for k, v in cli_overrides.items():
            path = k.split('.')
            cur = merged
            for p in path[:-1]:
                cur = cur.setdefault(p, {})
            cur[path[-1]] = v
    try:
        return AppCfg.model_validate(merged)
    except ValidationError as e:
        raise SystemExit(f"[config] invalid configuration: {e}")

def fingerprint(cfg: AppCfg) -> str:
    j = json.dumps(cfg.model_dump(mode="python"), sort_keys=True, separators=(",", ":"))
    return sha256(j.encode()).hexdigest()
