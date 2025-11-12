"""Fast path scanning and hashing for repository files.

Uses Rust-backed scanning and hashing when available (ft_fastpath), falls back to Python.
Both paths use BLAKE3 for deterministic, fast cryptographic hashing.
Respects .gitignore/.ignore files for scanning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

# Try to import Rust bridge AND ensure blake3 is available
_RUST_OK = False
try:
    import blake3  # Ensure available even when Rust path is used
    from ft_fastpath import (  # type: ignore[attr-defined]
        hash_files_parallel as _hash_rust,
        scan_repo_parallel as _scan_rust,
    )

    _RUST_OK = True
except Exception:
    # Rust module not available; we still need Python blake3 for deterministic fallback
    import blake3  # noqa: F401

    _RUST_OK = False

# Extra ignores beyond .gitignore (scanner already honors .gitignore)
_DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "build",
    "dist",
    "__pycache__",
    ".mypy_cache",
    ".firsttry",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
}
_DEFAULT_IGNORE_SUFFIXES = {".pyc", ".pyo", ".DS_Store"}


def _is_extra_ignored(p: Path) -> bool:
    """Check if a path should be ignored based on common project patterns."""
    parts = set(p.parts)
    if parts & _DEFAULT_IGNORE_DIRS:
        return True
    if p.suffix in _DEFAULT_IGNORE_SUFFIXES:
        return True
    return False


def scan_paths(root: Path, threads: int | None = None) -> list[Path]:
    """Return list of files under `root`. Uses Rust fastpath if available and not disabled."""
    root = Path(root)
    want = os.getenv("FT_FASTPATH", "auto").lower()
    use_rust = _RUST_OK and want != "off"

    if use_rust:
        t = threads or (os.cpu_count() or 4)
        entries = _scan_rust(str(root), int(t))
        return [Path(e.path) for e in entries if not _is_extra_ignored(Path(e.path))]

    # Fallback: basic os.walk with extra ignores
    out: list[Path] = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _DEFAULT_IGNORE_DIRS]
        for f in files:
            p = Path(r) / f
            if not _is_extra_ignored(p):
                out.append(p)
    return out


def hash_paths(paths: Iterable[Path]) -> dict[Path, str]:
    """Compute BLAKE3 digests for given paths.

    - Rust fastpath: parallel hashing via ft_fastpath/hash_files_parallel
    - Python fallback: streaming BLAKE3 (same algorithm)
    """
    want = os.getenv("FT_FASTPATH", "auto").lower()
    use_rust = _RUST_OK and want != "off"

    paths = list(paths)
    if use_rust:
        results = _hash_rust([str(p) for p in paths])
        return {Path(r.path): r.hash for r in results if r.hash}

    # --- Python fallback (BLAKE3, streaming) ---
    out: dict[Path, str] = {}
    for p in paths:
        try:
            h = blake3.blake3()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            out[p] = h.hexdigest()
        except Exception:
            # Unreadable file -> skip (consistent with Rust empty hash filtering)
            continue
    return out
