from __future__ import annotations
from pathlib import Path
import os

# (existing constants kept as-is)
IGNORE_DIRS: set[str] = {
    ".git", ".venv", ".venv-build", ".idea", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "dist", "build", ".next", "coverage", ".firsttry",
    "__pycache__", "benchmarks", "snapshots"
}

IGNORE_GLOBS: set[str] = {
    "**/.git/**", "**/.venv/**", "**/.pytest_cache/**", "**/.mypy_cache/**",
    "**/.ruff_cache/**", "**/node_modules/**", "**/dist/**", "**/build/**",
    "**/.next/**", "**/coverage/**", "**/.firsttry/**", "**/__pycache__/**",
}


def is_ignored(path: Path) -> bool:
    parts = set(path.parts)
    return any(p in IGNORE_DIRS for p in parts)


def bandit_excludes(repo_root: Path) -> list[str]:
    """
    Produce a conservative, comma-separated list for Bandit's -x, rooted at repo_root.
    Uses IGNORE_DIRS as the primary source. Users can override/extend with FT_BANDIT_EXCLUDES.
    """
    default_dirs = sorted({str(repo_root / d) for d in IGNORE_DIRS})
    env_extra = os.getenv("FT_BANDIT_EXCLUDES", "")
    extra = [e.strip() for e in env_extra.split(",") if e.strip()]
    # De-dup while preserving order: default first, then env overrides
    seen = set()
    out: list[str] = []
    for p in [*default_dirs, *extra]:
        try:
            rp = str(Path(p))
        except Exception:
            rp = p
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out

