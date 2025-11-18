from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from ..twin.hashers import hash_bytes, hash_file
from ..utils.proc import run_cmd as _sync_run_cmd


@dataclass
class RunResult:
    # Keep defaults for backward compatibility with older call sites that
    # constructed RunResult(status=..., message=..., etc.).
    name: str = ""
    rc: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: Optional[int] = None

    # Legacy/compat fields still used throughout the codebase
    status: str = ""
    ok: bool | None = None
    message: str = ""
    code: str = ""
    meta: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    tool: str | None = None


# Alias for backward compatibility
RunnerResult = RunResult


class CheckRunner(Protocol):
    """Lightweight protocol for the canonical, synchronous runner contract.

    New-style runners implement the sync `run(repo_root, files=None, *,
    timeout_s=None) -> RunResult` contract. This Protocol is used for static
    typing and new runner implementations.
    """

    check_id: str

    def prereq_check(self) -> str | None: ...

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str: ...

    def run(
        self, repo_root: Path, files: list[str] | None = None, *, timeout_s: int | None = None
    ) -> RunResult: ...


class BaseRunner:
    """Backward-compatible base class for the many async/legacy runners.

    Many existing runners in the codebase are async and call
    `await self.run_cmd(...)`. To preserve behavior while we migrate to the
    canonical `CheckRunner` Protocol, provide a small concrete base class
    that implements an `async run_cmd(...)` helper backed by the
    synchronous `run_cmd` utility.
    """

    check_id = ""

    def prereq_check(self) -> str | None:
        return None

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str:
        # conservative default: include tool/version + intent
        tv = ""
        env = ""
        tgt = hash_bytes(b"")
        cfg = hash_bytes(b"")
        intent = hash_bytes(b"")
        return hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    async def run(self, idx: int, ctx: dict[str, Any], item: dict[str, Any]) -> RunResult:
        """Legacy async runner entrypoint signature.

        Individual runners override this. The signature is intentionally kept
        compatible with existing implementations (idx, ctx, item).
        """
        raise NotImplementedError()

    async def run_cmd(
        self,
        name: str,
        tool: str,
        cmd: str,
        cwd: Path | str | None = None,
        timeout_s: int | None = None,
    ) -> RunResult:
        """Async wrapper around the synchronous `run_cmd` helper.

        Runs the blocking `run_cmd` in a thread to avoid blocking the event
        loop. Returns a `RunResult` with name/tool-normalized fields.
        """
        rc, out, err = await asyncio.to_thread(_sync_run_cmd, cmd, timeout_s)
        return RunResult(name=name, rc=rc, stdout=out or "", stderr=err or "")


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


def hash_targets(repo_root: Path, targets: list[str]) -> str:
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


# Backwards-compatible alias for callers that imported the private name.
_hash_targets = hash_targets


def hash_config(repo_root: Path, candidates: list[str]) -> str:
    parts: list[str] = []
    for rel in candidates:
        p = repo_root / rel
        if p.exists():
            parts.append(f"{rel}:{hash_file(p)}")
    if not parts:
        return hash_bytes(b"")
    return hash_bytes("|".join(parts).encode())


# Backwards-compatible alias for callers that imported the private name.
_hash_config = hash_config


def ensure_bin(name: str, alt: str | None = None) -> str | None:
    """Return None if binary is present (or alt is present), otherwise an error message."""
    if shutil.which(name):
        return None
    if alt and shutil.which(alt):
        return None
    return f"{name} executable not found. Install it and re-run."
