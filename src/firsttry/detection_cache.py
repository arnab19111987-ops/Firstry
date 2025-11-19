from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

# we keep this in the repo, not in $HOME, so it's per-repo
DETECT_CACHE_FILENAME = ".firsttry_detect_cache.json"
DEFAULT_TTL_SECONDS = 600  # 10 minutes


def _cache_path(repo_root: Path) -> Path:
    return repo_root / DETECT_CACHE_FILENAME


def load_detect_cache(
    repo_root: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> Optional[Dict[str, Any]]:
    path = _cache_path(repo_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None

    ts = data.get("ts")
    if ts is None:
        return None

    if (time.time() - ts) > ttl_seconds:
        # expired
        return None

    return data.get("payload")


def save_detect_cache(repo_root: Path, payload: Dict[str, Any]) -> None:
    path = _cache_path(repo_root)
    data = {
        "ts": time.time(),
        "payload": payload,
    }
    path.write_text(json.dumps(data, indent=2))
