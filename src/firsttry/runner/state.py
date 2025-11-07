"""Repository state fingerprinting for zero-run verification.

Computes a deterministic hash of all relevant source files, configs, and
environment to enable fast-path short-circuit when nothing changed since
last successful run.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterable

B3 = hashlib.blake2b
CACHE_DIR = Path(".firsttry/cache")
STATE_FILE = CACHE_DIR / "last_green_run.json"

INCLUDE_GLOBS = ["src/**/*.py", "tests/**/*.py", "pyproject.toml", "firsttry.toml"]


def _iter_files() -> Iterable[Path]:
    """Yield all files matching include globs."""
    for pat in INCLUDE_GLOBS:
        for p in Path().glob(pat):
            if p.is_file():
                yield p


def _hash_file(p: Path) -> bytes:
    """Hash a file's path and content."""
    h = B3(digest_size=16)
    h.update(str(p).encode())
    h.update(b"|")
    h.update(p.read_bytes())
    return h.digest()


def repo_fingerprint(extra: Dict[str, Any]) -> str:
    """Compute deterministic fingerprint of repository state.

    Args:
        extra: Additional key-value pairs to include in fingerprint

    Returns:
        Hex digest of repository state
    """
    h = B3(digest_size=16)
    # Tool/config/env salt
    salt = {
        "py": sys.version,
        "cwd": str(Path().resolve()),
        "ruff": os.environ.get("FT_RUFF_VER", ""),
        "mypy": os.environ.get("FT_MYPY_VER", ""),
        "pytest": os.environ.get("FT_PYTEST_VER", ""),
        "cfg": Path("firsttry.toml").read_text() if Path("firsttry.toml").exists() else "",
        **extra,
    }
    h.update(json.dumps(salt, sort_keys=True, separators=(",", ":")).encode())
    for p in sorted(_iter_files(), key=lambda x: str(x)):
        h.update(_hash_file(p))
    return h.hexdigest()


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
