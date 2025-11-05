from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess


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
    import sys
    import platform

    s = f"py={sys.version_info[:3]}|impl={platform.python_implementation()}|plat={platform.platform()}"
    return hash_bytes(s.encode())
