"""Cache utilities for warm path optimization and golden cache management.

Provides:
- Auto-refresh of golden cache from CI artifacts
- Flaky test memory (persistent across runs)
- Cache clear utilities
- Fingerprint-based cache validation
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

ARTIFACTS = Path("artifacts")
WARM_DIR = Path(".firsttry/warm")
FLAKY_FILE = Path("ci/flaky_tests.json")
FINGERPRINT_FILE = WARM_DIR / "fingerprint.txt"


def _run(cmd: list[str], timeout: float = 5.0) -> Tuple[int, str]:
    """Run a command with timeout, return (exit_code, output)."""
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            text=True,
            env=env,
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        stdout_str = str(e.stdout) if e.stdout else ""
        return 124, stdout_str + "\n[cache_utils] timeout\n"


def ensure_dirs() -> None:
    """Ensure required directories exist."""
    ARTIFACTS.mkdir(exist_ok=True)
    WARM_DIR.mkdir(parents=True, exist_ok=True)
    FLAKY_FILE.parent.mkdir(parents=True, exist_ok=True)


def compute_local_fingerprint() -> str:
    """Read local cache fingerprint."""
    return FINGERPRINT_FILE.read_text().strip() if FINGERPRINT_FILE.exists() else ""


def read_remote_fingerprint(ref: str = "origin/main") -> str:
    """Read cache fingerprint from remote ref. Non-blocking, best effort."""
    code, out = _run(
        ["git", "show", f"{ref}:.firsttry/warm/fingerprint.txt"], timeout=1.0
    )
    return out.strip() if code == 0 else ""


def auto_refresh_golden_cache(fetch_ref: str = "origin/main") -> None:
    """Run on EVERY ft command. Silent, ~1s budget. Keeps first run warm.
    
    Fetches latest main and checks if cache fingerprint changed.
    If changed, attempts to update cache from CI artifacts.
    """
    ensure_dirs()
    # Fetch latest (shallow, quiet)
    _run(["git", "fetch", fetch_ref.split("/")[0], "--quiet", "--depth=1"], timeout=1.0)
    
    local = compute_local_fingerprint()
    remote = read_remote_fingerprint(fetch_ref)
    
    if not remote or remote == local:
        return
    
    # Check if fingerprint file is stale (>1s old)
    try:
        mtime = FINGERPRINT_FILE.stat().st_mtime
    except FileNotFoundError:
        mtime = 0
    
    if time.time() - mtime > 1:
        try:
            update_cache(remote_fingerprint=remote)
        except Exception:
            pass  # never block user


def update_cache(remote_fingerprint: Optional[str] = None) -> None:
    """Download warm-cache-<fingerprint>.zip artifact via gh CLI (preferred).
    
    Args:
        remote_fingerprint: Explicit fingerprint to use. If None, auto-detect.
    """
    ensure_dirs()
    fp = (
        remote_fingerprint
        or compute_local_fingerprint()
        or read_remote_fingerprint("origin/main")
    )
    if not fp:
        return
    
    artifact = f"warm-cache-{fp}.zip"
    
    # GitHub CLI path (preferred in CI)
    rc, _ = _run(["which", "gh"], timeout=0.5)
    if rc == 0:
        rc2, _out = _run(
            ["gh", "run", "download", "--name", artifact, "--dir", str(ARTIFACTS)],
            timeout=10.0,
        )
        z = ARTIFACTS / artifact
        if rc2 == 0 and z.exists():
            _extract_zip(z, Path("."))
            return
    # Else: noop (prefer CI artifacts; we do not commit caches)


def _extract_zip(zip_path: Path, dest: Path) -> None:
    """Extract zip file to destination."""
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)


def read_flaky_tests() -> list[str]:
    """Read list of known flaky test nodeids from persistent storage.
    
    Returns:
        List of test nodeids (e.g., ["tests/test_foo.py::test_bar"])
    """
    ensure_dirs()
    if not FLAKY_FILE.exists():
        return []
    try:
        data = json.loads(FLAKY_FILE.read_text())
        return [str(x) for x in data.get("nodeids", [])]
    except Exception:
        return []


def clear_cache() -> None:
    """Nuke all local caches (warm, mypy, ruff, testmon)."""
    for p in (WARM_DIR, Path(".mypy_cache"), Path(".ruff_cache")):
        _rm_rf(p)
    # Common testmon db names (depending on backend)
    for p in (Path(".testmondata"), Path(".testmondata.sqlite")):
        if p.exists():
            p.unlink(missing_ok=True)


def _rm_rf(path: Path) -> None:
    """Recursively remove directory or file."""
    if not path.exists():
        return
    if path.is_file() or path.is_symlink():
        path.unlink(missing_ok=True)
        return
    for c in sorted(path.rglob("*"), reverse=True):
        try:
            if c.is_file() or c.is_symlink():
                c.unlink(missing_ok=True)
            else:
                c.rmdir()
        except Exception:
            pass
    try:
        path.rmdir()
    except Exception:
        pass
