"""Repository state fingerprinting for zero-run verification.

Computes a deterministic hash of all relevant source files, configs, and
environment to enable fast-path short-circuit when nothing changed since
last successful run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

CACHE_DIR = Path(".firsttry/cache")
STATE_FILE = CACHE_DIR / "last_green_run.json"

INCLUDE_GLOBS = ["src/**/*.py", "tests/**/*.py", "pyproject.toml", "firsttry.toml"]


def _iter_files() -> Iterable[Path]:
    """Yield all files matching include globs."""
    for pat in INCLUDE_GLOBS:
        for p in Path().glob(pat):
            if p.is_file():
                yield p


def _hash_file(p: Path) -> str:
    """Return a stable hex digest for a single file (path + content).

    Uses canonical BLAKE3 helpers to ensure parity with fastpath.
    """
    # Our hash_file only includes file content; prefix with path to avoid
    # collisions across different file names with same content.
    # Historically this project used 128-bit BLAKE2b digests (16 bytes -> 32 hex chars)
    # for repository fingerprinting. Tests rely on that 32-char output. Implement
    # a local helper here that produces a 16-byte blake2b hex digest.
    import hashlib

    content = p.read_bytes()
    # Hash file content first (16-byte blake2b)
    h1 = hashlib.blake2b(content, digest_size=16).hexdigest()
    combined = str(p).encode("utf-8") + b"|" + h1.encode("utf-8")
    return hashlib.blake2b(combined, digest_size=16).hexdigest()


def repo_fingerprint(extra: Dict[str, Any]) -> str:
    """Compute deterministic fingerprint of repository state.

    Args:
        extra: Additional key-value pairs to include in fingerprint

    Returns:
        Hex digest of repository state
    """
    # Build a deterministic payload: salt JSON + per-file digest entries
    salt = {
        "py": sys.version,
        "cwd": str(Path().resolve()),
        "ruff": os.environ.get("FT_RUFF_VER", ""),
        "mypy": os.environ.get("FT_MYPY_VER", ""),
        "pytest": os.environ.get("FT_PYTEST_VER", ""),
        "cfg": Path("firsttry.toml").read_text() if Path("firsttry.toml").exists() else "",
        **extra,
    }
    parts: list[bytes] = [json.dumps(salt, sort_keys=True, separators=(",", ":")).encode()]
    for p in sorted(_iter_files(), key=lambda x: str(x)):
        try:
            parts.append(_hash_file(p).encode("utf-8"))
        except Exception:
            # best-effort: skip unreadable files
            continue
    # Final fingerprint uses 16-byte blake2b to match historical format
    import hashlib

    final = hashlib.blake2b(digest_size=16)
    final.update(b"||".join(parts))
    return final.hexdigest()


def load_last_green() -> Dict[str, Any] | None:
    """Load last successful run state from cache.

    Returns:
        Dict with fingerprint and report, or None if not available
    """
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return None


def save_last_green(data: Dict[str, Any]) -> None:
    """Save successful run state to cache.

    Args:
        data: Dict containing fingerprint and report
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, separators=(",", ":")))
