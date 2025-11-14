from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable

import blake3


# Internal helper: one canonical BLAKE3 interface for the whole app.
def _new_b3() -> Any:
    # blake3's runtime object has no typed stub in this environment; use Any
    # to keep type-checking stable while preserving runtime behaviour.
    return blake3.blake3()


def hash_bytes(data: bytes) -> str:
    """Return a hex digest for arbitrary bytes using BLAKE3.

    This must remain stable across Python-only and Rust ft_fastpath paths.
    """
    h = _new_b3()
    h.update(data)
    return h.hexdigest()


def hash_file(path: Path) -> str:
    """Return a hex digest for a single file using BLAKE3."""
    h = _new_b3()
    # Stream to avoid loading big files into memory:
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_files(paths: Iterable[Path]) -> str:
    """Return a combined digest for a set of files (order-independent)."""
    h = _new_b3()
    for p in sorted(map(str, paths)):
        p_path = Path(p)
        h.update(p_path.as_posix().encode("utf-8"))
        if p_path.is_file():
            with p_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
    return h.hexdigest()


def tool_version_hash(tool_cmd: list[str]) -> str:
    """Return a digest representing the stdout/stderr of a tool invocation.

    Kept for compatibility with existing callers.
    """
    try:
        import subprocess

        out = subprocess.run(tool_cmd, capture_output=True, text=True, check=False)
        data = (out.stdout or out.stderr or "").strip().encode()
        return hash_bytes(data)
    except Exception:
        return hash_bytes(b"")


def env_fingerprint() -> str:
    """Small, deterministic fingerprint of the runtime environment."""
    import platform
    import sys

    s = f"py={sys.version_info[:3]}|impl={platform.python_implementation()}|plat={platform.platform()}"
    return hash_bytes(s.encode("utf-8"))


@dataclass
class Hasher:
    """High-level hasher facade.

    This delegates to ft_fastpath when available or falls back to the
    pure-Python scanner/hash functions above.
    """

    root: Path

    def enumerate_files(self) -> list[Path]:
        from .fastpath import scan_paths

        return scan_paths(self.root)

    def compute_hashes(self, files: list[Path]) -> dict[Path, str]:
        # Prefer native parallel implementation if available
        try:
            from .ft_fastpath import hash_files_parallel

            # hash_files_parallel returns list[(str,str)]
            pairs = hash_files_parallel([str(p) for p in files])
            return {Path(k): v for k, v in pairs}
        except Exception:
            return {p: hash_file(p) for p in files}

    def hash_all(self) -> dict[Path, str]:
        files = self.enumerate_files()
        return self.compute_hashes(files)
