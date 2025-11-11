from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..twin.hashers import hash_bytes, hash_file


@dataclass
class RunResult:
    status: str
    # subprocess outputs are sometimes bytes (when callers omit text=True)
    # keep the type permissive to reduce friction; callers should decode when
    # they need string content.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    meta: dict[str, Any] | None = None


# Alias for backward compatibility
RunnerResult = RunResult


class CheckRunner(Protocol):
    check_id: str

    def prereq_check(self) -> str | None: ...

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str: ...

    def run(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
        *,
        timeout_s: int,
    ) -> RunResult: ...


# Alias for backward compatibility
BaseRunner = CheckRunner


# Files and directories to ignore when hashing for cache keys
# Ignoring these prevents spurious cache misses from build artifacts
IGNORE_FILES = {
    ".coverage",
    "coverage.xml",
    ".coverage.har",
    "htmlcov",
    ".pytest_cache",
}

IGNORE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".firsttry",
    ".venv",
    ".venv-build",
    "htmlcov",
    ".coverage",
    "node_modules",
    ".tox",
    ".eggs",
    "dist",
    "build",
}


def _should_ignore_path(path: Path) -> bool:
    """Check if a path should be ignored for cache hashing."""
    # Ignore specific filenames
    if path.name in IGNORE_FILES:
        return True
    # Ignore paths containing any ignored directory
    parts = set(path.parts)
    if parts & IGNORE_DIRS:
        return True
    return False


def _hash_targets(repo_root: Path, targets: list[str]) -> str:
    # Hash the CONTENTS of files under all target paths (intent, not cmd)
    parts: list[str] = []
    for t in sorted(set(targets or [])):
        p = repo_root / t
        if p.is_dir():
            for f in sorted(p.rglob("*.py")):
                if _should_ignore_path(f):
                    continue
                parts.append(f"{f.as_posix()}::{hash_file(f)}")
        elif p.is_file():
            if not _should_ignore_path(p):
                parts.append(f"{p.as_posix()}::{hash_file(p)}")
    return hash_bytes("||".join(parts).encode())


def _hash_config(repo_root: Path, candidates: list[str]) -> str:
    parts = []
    for rel in candidates:
        p = repo_root / rel
        if p.exists():
            parts.append(f"{rel}:{hash_file(p)}")
    if not parts:
        return hash_bytes(b"")
    return hash_bytes("|".join(parts).encode())


def ensure_bin(name: str, alt: str | None = None) -> str | None:
    """Return None if binary is present (or alt is present), otherwise an error message."""
    if shutil.which(name):
        return None
    if alt and shutil.which(alt):
        return None
    return f"{name} executable not found. Install it and re-run."
