from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Protocol, Optional
import shutil
from ..twin.hashers import hash_bytes, hash_file


@dataclass
class RunResult:
    status: str
    # subprocess outputs are sometimes bytes (when callers omit text=True)
    # keep the type permissive to reduce friction; callers should decode when
    # they need string content.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    meta: Dict[str, Any] | None = None


class CheckRunner(Protocol):
    check_id: str

    def prereq_check(self) -> Optional[str]: ...

    def build_cache_key(self, repo_root: Path, targets: List[str], flags: List[str]) -> str: ...

    def run(self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int) -> RunResult: ...


def _hash_targets(repo_root: Path, targets: List[str]) -> str:
    # Hash the CONTENTS of files under all target paths (intent, not cmd)
    parts: List[str] = []
    for t in sorted(set(targets or [])):
        p = (repo_root / t)
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