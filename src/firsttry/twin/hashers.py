from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def hash_bytes(b: bytes) -> str:
    return hashlib.blake2b(b, digest_size=16).hexdigest()


def hash_file(p: Path) -> str:
    h = hashlib.blake2b(digest_size=16)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_dir(paths: list[Path]) -> str:
    h = hashlib.blake2b(digest_size=16)
    for p in sorted(paths):
        h.update(p.as_posix().encode())
        h.update(hash_file(p).encode())
    return h.hexdigest()


def tool_version_hash(tool_cmd: list[str]) -> str:
    try:
        out = subprocess.run(tool_cmd, capture_output=True, text=True, check=False)
        data = (out.stdout or out.stderr or "").strip().encode()
        return hash_bytes(data)
    except Exception:
        return hash_bytes(b"")


def env_fingerprint() -> str:
    # Keep it cheap and deterministic: python version + platform
    import platform
    import sys

    s = f"py={sys.version_info[:3]}|impl={platform.python_implementation()}|plat={platform.platform()}"
    return hash_bytes(s.encode())


class Hasher:
    """High-level hasher for computing repository file digests using BLAKE3.

    Combines fast-path scanning with BLAKE3 hashing for deterministic
    repository fingerprinting and change detection.
    """

    def __init__(self, root: Path):
        """Initialize hasher for a repository root."""
        from .fastpath import scan_paths

        self.root = Path(root)
        self._scan_paths = scan_paths

    def enumerate_files(self) -> list[Path]:
        """Enumerate all discoverable files in the repository."""
        files = self._scan_paths(self.root)
        return files

    def compute_hashes(self, files: list[Path]) -> dict[Path, str]:
        """Compute BLAKE3 digests for given files."""
        from .fastpath import hash_paths

        return hash_paths(files)

    def hash_all(self) -> dict[Path, str]:
        """Enumerate and hash all repository files in one call."""
        files = self.enumerate_files()
        return self.compute_hashes(files)
