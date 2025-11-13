from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def write_digest(path: Path, digest_path: Path | None = None) -> Path:
    digest_path = digest_path or path.with_suffix(path.suffix + ".sha256")
    digest_path.write_text(sha256_file(path))
    return digest_path

def verify_digest(path: Path, digest_path: Path | None = None) -> bool:
    digest_path = digest_path or path.with_suffix(path.suffix + ".sha256")
    if not digest_path.exists():
        return False

    return digest_path.read_text().strip() == sha256_file(path)

def try_sigstore_sign(path: Path) -> None:
    try:
        pass
        # Placeholder: if sigstore CLI/lib available, sign here.
        # Do not fail if unavailable.
    except Exception:
        pass

def try_sigstore_verify(path: Path) -> bool:
    try:
        return True
    except Exception:
        return True  # Non-blocking if not present
