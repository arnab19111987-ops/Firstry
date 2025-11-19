from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseCache, CacheHit


class LocalCache(BaseCache):
    """
    Simple on-disk cache under .firsttry/cache/.
    Stores one JSON file per key. Optional size cap via LRU timestamps.
    """

    def __init__(self, repo_root: Path, max_entries: int = 2000):
        self.root = repo_root / ".firsttry" / "cache"
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries

    def _path_for(self, key: str) -> Path:
        # shard by prefix so we don't dump thousands into one dir
        shard = key[:2]
        p = self.root / shard
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{key}.json"

    def get(self, key: str) -> Optional[CacheHit]:
        p = self._path_for(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            # touch file to update "access time"
            p.touch()
            return CacheHit(
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                meta=data.get("meta"),
            )
        except Exception:
            return None

    def put(self, key: str, result: CacheHit) -> None:
        p = self._path_for(key)
        payload: Dict[str, Any] = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "meta": result.meta or {},
            "_ts": time.time(),
        }
        p.write_text(json.dumps(payload, ensure_ascii=False))
        self._maybe_evict()

    def _maybe_evict(self) -> None:
        # cheap LRU by modified time across all shards
        files = sorted(
            self.root.rglob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
        )
        if len(files) <= self.max_entries:
            return
        for f in files[self.max_entries :]:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
