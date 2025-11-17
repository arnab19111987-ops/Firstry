"""Per-task caching to skip individual tools when inputs haven't changed.

Each task maintains a cache of previous successful runs keyed by command,
inputs (file paths + content), and salt (env/config). When a task's inputs
are unchanged, it can be skipped with a cache hit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from firsttry.twin.hashers import hash_bytes

DIR = Path(".firsttry/cache/tasks")


def key_for(task_id: str, cmd: list[str], inputs: Iterable[str], salt: Dict[str, Any]) -> str:
    """Compute cache key for a task.

    Args:
        task_id: Unique task identifier
        cmd: Command and arguments
        inputs: File/directory paths that affect task output
        salt: Additional metadata (env vars, config, versions)

    Returns:
        Hex digest cache key
    """
    # Build a deterministic payload and return a BLAKE3 digest
    parts: list[bytes] = []
    parts.append(("id:" + task_id).encode())
    parts.append(("cmd:" + " ".join(cmd)).encode())
    for s in sorted(salt.items()):
        parts.append(str(s).encode())
    for p in sorted(inputs):
        P = Path(p)
        if not P.exists():
            continue
        if P.is_dir():
            for f in sorted(P.rglob("*.py")):
                if f.is_file():
                    parts.append(("f:" + str(f)).encode())
                    parts.append(f.read_bytes())
        else:
            parts.append(("f:" + str(P)).encode())
            parts.append(P.read_bytes())
    return hash_bytes(b"||".join(parts))


def get(task_id: str, key: str) -> Dict[str, Any] | None:
    """Retrieve cached task result.

    Args:
        task_id: Task identifier
        key: Cache key

    Returns:
        Cached result dict or None if not found
    """
    p = DIR / task_id / (key + ".json")
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def put(task_id: str, key: str, result: Dict[str, Any]) -> None:
    """Store task result in cache.

    Args:
        task_id: Task identifier
        key: Cache key
        result: Result dict to cache
    """
    d = DIR / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / (key + ".json")).write_text(json.dumps(result, separators=(",", ":")))
