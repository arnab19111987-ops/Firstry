from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - for older envs
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class Config:
    """
    Canonical FirstTry config object.

    - raw: merged TOML from project + user config.
    - workflow_requires: mapping from check_id -> list of dependency check_ids.
    - s3_bucket / s3_region / s3_prefix: remote cache / artifact settings.
    """
    raw: Mapping[str, Any] = field(default_factory=dict)
    workflow_requires: Dict[str, List[str]] = field(default_factory=dict)
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_prefix: Optional[str] = None


# Module-local singleton cache keyed by root path
_CONFIG_CACHE: dict[Path, Config] = {}


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if (
            k in out
            and isinstance(out[k], dict)
            and isinstance(v, dict)
        ):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_raw_config(root: Path) -> dict[str, Any]:
    """
    Load and merge config from:
      1. firsttry.toml in the repo root
      2. ~/.config/firsttry/config.toml (if present)
      3. Environment overrides (simple keys for now)
    """
    root = root.resolve()
    proj_cfg = _load_toml(root / "firsttry.toml")

    # User-level config (~/.config/firsttry/config.toml)
    home = Path(os.environ.get("HOME", str(Path.home()))).expanduser()
    user_cfg = _load_toml(home / ".config" / "firsttry" / "config.toml")

    merged = _deep_merge(proj_cfg, user_cfg)

    # Simple env overrides (extend as needed)
    # Example: FT_S3_BUCKET, FT_S3_REGION, FT_S3_PREFIX
    cache_remote = merged.setdefault("cache", {})
    remote = merged.setdefault("remote", {})

    env_bucket = os.getenv("FT_S3_BUCKET")
    env_region = os.getenv("FT_S3_REGION")
    env_prefix = os.getenv("FT_S3_PREFIX")

    if env_bucket:
        remote["bucket"] = env_bucket
    if env_region:
        remote["region"] = env_region
    if env_prefix:
        remote["prefix"] = env_prefix

    # Ensure cache.remote is explicit and default-off
    cache_remote.setdefault("remote", False)

    return merged


def _extract_workflow_requires(raw: Mapping[str, Any]) -> dict[str, List[str]]:
    """
    Normalize [workflow] section into:
      check_id -> list[check_id]
    Example:
      [workflow]
      pytest = ["ruff", "mypy"]
      mypy = "ruff"
    """
    workflow_section = raw.get("workflow") or {}
    if not isinstance(workflow_section, Mapping):
        return {}

    out: dict[str, List[str]] = {}
    for check_id, value in workflow_section.items():
        if isinstance(value, str):
            deps = [value]
        elif isinstance(value, list):
            deps = [str(v) for v in value]
        else:
            continue
        out[str(check_id)] = deps
    return out


def _extract_s3_settings(raw: Mapping[str, Any]) -> dict[str, str | None]:
    remote = raw.get("remote") or {}
    if not isinstance(remote, Mapping):
        remote = {}

    bucket = remote.get("bucket")
    region = remote.get("region")
    prefix = remote.get("prefix")

    return {
        "bucket": str(bucket) if bucket else None,
        "region": str(region) if region else None,
        "prefix": str(prefix) if prefix else None,
    }


def get_config(root: Path | None = None) -> Config:
    """
    Return the canonical Config for the given root (or CWD).
    Cached per-root to avoid repeated I/O.
    """
    if root is None:
        root = Path.cwd()
    root = root.resolve()

    cached = _CONFIG_CACHE.get(root)
    if cached is not None:
        return cached

    raw = _load_raw_config(root)
    workflow_requires = _extract_workflow_requires(raw)
    s3 = _extract_s3_settings(raw)

    cfg = Config(
        raw=raw,
        workflow_requires=workflow_requires,
        s3_bucket=s3["bucket"],
        s3_region=s3["region"],
        s3_prefix=s3["prefix"],
    )
    _CONFIG_CACHE[root] = cfg
    return cfg


def get_workflow_requires(root: Path | None = None) -> dict[str, List[str]]:
    return dict(get_config(root).workflow_requires)


def get_s3_settings(root: Path | None = None) -> dict[str, Optional[str]]:
    cfg = get_config(root)
    return {
        "bucket": cfg.s3_bucket,
        "region": cfg.s3_region,
        "prefix": cfg.s3_prefix,
    }
