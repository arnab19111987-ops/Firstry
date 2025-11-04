from __future__ import annotations
from pathlib import Path

# Default, repo-wide. Allow overrides via config_loader later.
IGNORE_DIRS: set[str] = {
    ".git", ".venv", ".venv-build", ".idea", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "dist", "build", ".next", "coverage", ".firsttry",
    "__pycache__", "benchmarks", "snapshots",
}

IGNORE_GLOBS: set[str] = {
    "**/.git/**", "**/.venv/**", "**/.pytest_cache/**", "**/.mypy_cache/**",
    "**/.ruff_cache/**", "**/node_modules/**", "**/dist/**", "**/build/**",
    "**/.next/**", "**/coverage/**", "**/.firsttry/**", "**/__pycache__/**",
}


def is_ignored(path: Path) -> bool:
    """Return True if any path part matches the repo-wide ignore set.

    This is intentionally conservative: it only checks path.parts membership
    against the configured IGNORE_DIRS.
    """
    parts = set(path.parts)
    return any(d in parts for d in IGNORE_DIRS)
