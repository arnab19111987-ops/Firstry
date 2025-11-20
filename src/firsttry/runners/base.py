from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from ..twin.hashers import hash_bytes, hash_file


@dataclass
class RunResult:
    status: str = ""
    # subprocess outputs are sometimes bytes (when callers omit text=True)
    # keep the type permissive to reduce friction; callers should decode when
    # they need string content.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    meta: Dict[str, Any] | None = None
    # Backwards-compatible fields used in various runner implementations
    name: str | None = None
    ok: bool | None = None
    message: str | None = None
    tool: str | None = None
    extra: Any | None = None
    cmd: Any | None = None
    duration_s: float | None = None
    duration_ms: int | None = None
    # Optional short machine-readable code (e.g. ruff/mypy rule code)
    code: str | None = None


class CheckRunner(Protocol):
    check_id: str

    def prereq_check(self) -> Optional[str]: ...

    def build_cache_key(
        self, repo_root: Path, targets: List[str], flags: List[str]
    ) -> str: ...

    # Allow flexible runner signatures to support both the legacy
    # repo-root-based and the newer index/ctx/item coroutine styles used
    # across the codebase. Use a permissive signature to avoid spurious
    # mypy override errors while still documenting the general intent.
    def run(self, *args: Any, **kwargs: Any) -> Any: ...

    pass


def _hash_targets(repo_root: Path, targets: List[str]) -> str:
    # Hash the CONTENTS of files under all target paths (intent, not cmd)
    parts: List[str] = []
    for t in sorted(set(targets or [])):
        p = repo_root / t
        if p.is_dir():
            for f in sorted(p.rglob("*.py")):
                parts.append(f"{f.as_posix()}::{hash_file(f)}")
        elif p.is_file():
            parts.append(f"{p.as_posix()}::{hash_file(p)}")
    return hash_bytes("||".join(parts).encode())


def _hash_config(repo_root: Path, candidates: List[str]) -> str:
    parts = []
    for rel in candidates:
        p = repo_root / rel
        if p.exists():
            parts.append(f"{rel}:{hash_file(p)}")
    if not parts:
        return hash_bytes(b"")
    return hash_bytes("|".join(parts).encode())


def ensure_bin(name: str, alt: str | None = None) -> Optional[str]:
    """Return None if binary is present (or alt is present), otherwise an error message."""
    if shutil.which(name):
        return None
    if alt and shutil.which(alt):
        return None
    return f"{name} executable not found. Install it and re-run."


# Backwards-compatibility aliases for older runner implementations/tests
# Some modules expect the older names `BaseRunner` and `RunnerResult`;
# provide aliases so those imports keep working.
BaseRunner = CheckRunner
RunnerResult = RunResult
