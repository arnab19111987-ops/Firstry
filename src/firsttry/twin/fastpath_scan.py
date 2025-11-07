"""Fast path scanning for repository files.

Uses Rust-backed scan when available (ft_fastpath), falls back to Python os.walk.
Respects .gitignore/.ignore files and provides caching metadata (size, mtime).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

_RUST_OK = False
try:
    from ft_fastpath import scan_repo_parallel as _scan_rust  # type: ignore[attr-defined]

    _RUST_OK = True
except Exception:
    _RUST_OK = False

# Extra project-specific ignores beyond .gitignore (folders or glob-ish suffixes)
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


def scan_paths(root: Path, threads: int | None = None) -> List[Path]:
    """
    Returns a list of file Paths under `root`.

    Prefers Rust fast-path; falls back to Python os.walk.
    Respects .gitignore/.ignore via Rust; Python fallback only applies basic ignores.

    Args:
        root: Root directory to scan
        threads: Number of threads for parallel scanning (auto-detect if None)

    Returns:
        List of Path objects for all discovered files
    """
    root = Path(root)

    if _RUST_OK and os.getenv("FT_FASTPATH", "auto").lower() != "off":
        t = threads or (os.cpu_count() or 4)
        entries = _scan_rust(str(root), int(t))
        # Filter any project-specific ignores on top of .gitignore
        rust_out = []
        for e in entries:
            p = Path(e.path)
            if not _is_extra_ignored(p):
                rust_out.append(p)
        return rust_out

    # --- Python fallback (basic) ---
    out: list[Path] = []
    for r, dirs, files in os.walk(root):
        # prune directories aggressively
        dirs[:] = [d for d in dirs if d not in _DEFAULT_IGNORE_DIRS]
        for f in files:
            p = Path(r) / f
            if not _is_extra_ignored(p):
                out.append(p)
    return out
