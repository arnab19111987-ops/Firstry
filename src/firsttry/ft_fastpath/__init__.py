# Python shim for ft_fastpath. Provides pure-python fallbacks when
# the compiled Rust extension is not built/installed. Tests expect the
# module to expose `hash_files_parallel` and (optionally) `scan_repo_parallel`.

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable
from typing import List
from typing import Tuple

_native = None
try:
    # If a compiled extension exists, it will be available as _ft_fastpath
    from . import _ft_fastpath as _native  # type: ignore
except Exception:
    _native = None


def hash_files_parallel(paths: Iterable[str]) -> List[Tuple[str, str]]:
    """Return list of (path, blake3_hex) for each path.

    If a native implementation is present, delegate to it. Otherwise
    fall back to a simple single-threaded Python implementation using
    the `blake3` package.
    """
    if _native is not None and hasattr(_native, "hash_files_parallel"):
        return list(_native.hash_files_parallel(paths))

    try:
        import blake3
    except Exception as e:  # pragma: no cover - blake3 availability is external
        raise RuntimeError("blake3 is required for Python fastpath fallback") from e

    out: List[Tuple[str, str]] = []
    for p in paths:
        try:
            b = Path(p).read_bytes()
            out.append((p, blake3.blake3(b).hexdigest()))
        except Exception:
            out.append((p, ""))
    return out


def scan_repo_parallel(root: str | Path, patterns: Iterable[str] | None = None) -> Iterable[str]:
    """Naive repo scanner fallback. Yields file paths under root.

    Delegates to native implementation when available.
    """
    if _native is not None and hasattr(_native, "scan_repo_parallel"):
        for p in _native.scan_repo_parallel(str(root), list(patterns or [])):
            yield p
        return

    rootp = Path(root)
    for dirpath, _dirs, files in os.walk(rootp):
        for f in files:
            yield os.path.join(dirpath, f)


__all__ = ["hash_files_parallel", "scan_repo_parallel"]
