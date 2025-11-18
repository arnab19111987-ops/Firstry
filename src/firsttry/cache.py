from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .cache_models import InputFileMeta, ToolCacheEntry
from .cache_utils import get_cache_state

# Global cache file (can be monkeypatched in tests)
CACHE_FILE: Path | None = None

# Default location when CACHE_FILE is not overridden by tests
CACHE_DIR = Path(os.path.expanduser("~")) / ".firsttry"
_DEFAULT_CACHE_FILE = CACHE_DIR / "cache.json"

# Local cache for legacy compatibility
CACHE_DIRNAME = ".firsttry"
CACHE_FILENAME = "cache.json"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_file_path() -> Path:
    """Return the filesystem path for the global cache file.

    If tests set ``firsttry.cache.CACHE_FILE`` to a Path, honor that value.
    Otherwise fall back to the conventional location under the user's home
    directory.
    """
    if CACHE_FILE is not None:
        return Path(CACHE_FILE)
    return _DEFAULT_CACHE_FILE


def load_cache() -> dict[str, Any]:
    """Load global cache from home directory

    Compute the cache path first so tests can monkeypatch `CACHE_FILE` to
    a temporary path without triggering creation/reads of the user's
    home-based cache directory. Only ensure the default cache directory
    exists when we're actually using the default path.
    """
    p = _get_cache_file_path()
    # Only create the default cache dir when we're using the default path
    if p == _DEFAULT_CACHE_FILE or str(p).startswith(str(CACHE_DIR)):
        _ensure_dir()

    if not Path(p).exists():
        return {"repos": {}}
    try:
        with Path(p).open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"repos": {}}

    # Defensive normalization: tests expect a dict with a "repos" mapping.
    if not isinstance(data, dict):
        return {"repos": {}}
    repos = data.get("repos")
    if not isinstance(repos, dict):
        return {"repos": {}}
    return data


def save_cache(data: dict[str, Any]) -> None:
    """Save global cache to home directory"""
    _ensure_dir()
    p = _get_cache_file_path()
    with Path(p).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a single file"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_paths(paths: Iterable[Path]) -> str:
    """Compute SHA256 hash of multiple files (sorted by path)"""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        h.update(str(p).encode("utf-8"))
        if p.exists() and p.is_file():
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        elif p.exists() and p.is_dir():
            # For directories, just hash the path name
            h.update(f"dir:{p}".encode())
    return h.hexdigest()


def get_repo_cache(repo_root: str) -> dict[str, Any]:
    """Get cache data for a specific repository"""
    data = load_cache()
    if "repos" not in data:
        data["repos"] = {}
    return data["repos"].get(repo_root, {"tools": {}})


def update_repo_cache(repo_root: str, repo_data: dict[str, Any]) -> None:
    """Update cache data for a specific repository"""
    data = load_cache()
    data["repos"][repo_root] = repo_data
    save_cache(data)


def is_tool_cache_valid(
    repo_root: str,
    tool_name: str,
    input_hash: str,
) -> bool:
    """Check if tool cache is valid for given inputs"""
    repo_data = get_repo_cache(repo_root)
    tool_data = repo_data.get("tools", {}).get(tool_name)
    if not tool_data:
        return False
    return tool_data.get("input_hash") == input_hash and tool_data.get("status") == "ok"


def write_tool_cache(
    repo_root: str,
    tool_name: str,
    input_hash: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write tool result to cache"""
    repo_data = get_repo_cache(repo_root)
    tools = repo_data.setdefault("tools", {})
    payload = {
        "input_hash": input_hash,
        "status": status,
    }
    if extra:
        payload.update(extra)
    tools[tool_name] = payload
    update_repo_cache(repo_root, repo_data)


# Legacy compatibility functions for existing code
def _cache_file(root: Path) -> Path:
    d = root / CACHE_DIRNAME
    d.mkdir(exist_ok=True)
    return d / CACHE_FILENAME


def load_cache_legacy(root: Path) -> dict[str, Any]:
    p = _cache_file(root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        # corrupted or old cache → ignore
        return {}


def save_cache_legacy(root: Path, data: dict[str, Any]) -> None:
    p = _cache_file(root)
    data["updated_at"] = time.time()
    p.write_text(json.dumps(data, indent=2))


def should_skip_gate(cache: dict, gate_id: str, changed_files: list[str]) -> bool:
    """Return True if we can safely skip this gate because:
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


# Enhanced cache functions using stat-first validation


def load_tool_cache_entry(repo_root: str, tool_name: str) -> ToolCacheEntry | None:
    """Load enhanced cache entry with stat-first validation support."""
    repo_data = get_repo_cache(repo_root)
    tools = repo_data.get("tools", {})
    tool_data = tools.get(tool_name)

    if not tool_data:
        return None

    try:
        # Try to load as enhanced cache entry
        if "input_files" in tool_data:
            input_files = [InputFileMeta(**f) for f in tool_data["input_files"]]
            return ToolCacheEntry(
                tool_name=tool_name,
                input_files=input_files,
                input_hash=tool_data["input_hash"],
                status=tool_data["status"],
                created_at=tool_data.get("created_at", time.time()),
                extra=tool_data.get("extra", {}),
            )
    except (KeyError, TypeError):
        pass

    return None


def save_tool_cache_entry(repo_root: str, entry: ToolCacheEntry) -> None:
    """Save enhanced cache entry with file metadata."""
    cache = load_cache()
    repo_data = cache.setdefault("repos", {}).setdefault(repo_root, {})
    tools = repo_data.setdefault("tools", {})

    tools[entry.tool_name] = {
        "input_files": [
            {
                "path": f.path,
                "size": f.size,
                "mtime": f.mtime,
            }
            for f in entry.input_files
        ],
        "input_hash": entry.input_hash,
        "status": entry.status,
        "created_at": entry.created_at,
        "extra": entry.extra,
    }

    save_cache(cache)


def is_tool_cache_valid_fast(
    repo_root: str,
    tool_name: str,
    input_paths: list[str],
) -> tuple[bool, str]:
    """Fast cache validation using stat-first approach.

    Returns (is_valid, cache_state) where cache_state is:
    - "hit": Valid cache, use result
    - "miss": No cache or files changed
    - "policy-rerun": Valid cache but policy says re-run (e.g., failed tools)
    - "stale": Cache too old
    """
    entry = load_tool_cache_entry(repo_root, tool_name)
    cache_state, use_cache = get_cache_state(
        entry,
        input_paths,
        policy_rerun_failures=True,
    )
    return use_cache, cache_state


def invalidate_tool_cache(repo_root: str, tool_name: str) -> None:
    """Invalidate cache for a specific tool."""
    repo_data = get_repo_cache(repo_root)
    tools = repo_data.get("tools", {})
    if tool_name in tools:
        del tools[tool_name]
        save_cache(load_cache())  # Update the global cache


def clear_repo_cache(repo_root: str) -> None:
    """Clear all cache for a specific repository."""
    cache_data = load_cache()
    if repo_root in cache_data.get("repos", {}):
        del cache_data["repos"][repo_root]
        save_cache(cache_data)
