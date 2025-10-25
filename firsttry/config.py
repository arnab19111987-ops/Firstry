from __future__ import annotations

import os
import pathlib
import typing as t
import yaml  # type: ignore[import-untyped]


class FirstTryConfig(t.TypedDict, total=False):
    python_versions: t.List[str]
    skip: t.List[str]
    db_url: str


DEFAULT_CONFIG: FirstTryConfig = {
    "python_versions": [],
    "skip": [],
}


def load_config_file(path: pathlib.Path) -> FirstTryConfig:
    """
    Read a .firsttry.yml/.yaml file and return a sanitized dict.
    On parse error or missing file, return {} (not raising).
    """
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    out: FirstTryConfig = {}
    if "python_versions" in data and isinstance(data["python_versions"], list):
        out["python_versions"] = [str(v) for v in data["python_versions"]]
    if "skip" in data and isinstance(data["skip"], list):
        out["skip"] = [str(v) for v in data["skip"]]
    if "db_url" in data and isinstance(data["db_url"], str):
        out["db_url"] = data["db_url"]
    return out


def discover_config(start: os.PathLike[str] | str = ".") -> FirstTryConfig:
    """
    Walk upward from `start` looking for .firsttry.yml or .firsttry.yaml.
    Merge DEFAULT_CONFIG with any discovered file.
    """
    cur = pathlib.Path(start).resolve()
    root = cur.anchor

    found: FirstTryConfig | None = None

    while True:
        cand1 = cur / ".firsttry.yml"
        cand2 = cur / ".firsttry.yaml"
        if cand1.exists():
            found = load_config_file(cand1)
            break
        if cand2.exists():
            found = load_config_file(cand2)
            break

        if str(cur) == root:
            break
        cur = cur.parent

    merged: FirstTryConfig = {}
    merged.update(DEFAULT_CONFIG)
    if found:
        merged.update(found)
    return merged
