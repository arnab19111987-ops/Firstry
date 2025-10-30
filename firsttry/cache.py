from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

CACHE_DIRNAME = ".firsttry"
CACHE_FILENAME = "cache.json"


def _cache_file(root: Path) -> Path:
    d = root / CACHE_DIRNAME
    d.mkdir(exist_ok=True)
    return d / CACHE_FILENAME


def load_cache(root: Path) -> Dict[str, Any]:
    p = _cache_file(root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        # corrupted or old cache → ignore
        return {}


def save_cache(root: Path, data: Dict[str, Any]) -> None:
    p = _cache_file(root)
    data["updated_at"] = time.time()
    p.write_text(json.dumps(data, indent=2))


def should_skip_gate(cache: dict, gate_id: str, changed_files: list[str]) -> bool:
    """
    Return True if we can safely skip this gate because:
    - we have previous run info
    - and none of the changed files are in the watched list
    """
    gates = cache.get("gates", {})
    info = gates.get(gate_id)
    if not info:
        return False
    watched = info.get("watched") or []
    if not watched:
        return False
    return not any(f in watched for f in changed_files)


def update_gate_cache(cache: dict, gate_id: str, watched_files: list[str]) -> None:
    gates = cache.setdefault("gates", {})
    gates[gate_id] = {
        "watched": watched_files,
        "last_ok": True,
    }
