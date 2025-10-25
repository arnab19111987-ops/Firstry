"""
Forwarder: expose the canonical root-level licensing cache API.

Tests and runtime should import from `firsttry.license_cache`, which is defined
at the repository root under `firsttry/license_cache.py`. This thin wrapper
re-exports that module's public API to keep a single source of truth without
using star imports (keeps linters happy).
"""

from firsttry import license_cache as _lc

CachedLicense = _lc.CachedLicense
save_cache = _lc.save_cache
load_cache = _lc.load_cache
is_fresh = _lc.is_fresh
assert_license = _lc.assert_license
remote_verify = _lc.remote_verify
CACHE_PATH = _lc.CACHE_PATH
FRESH_FOR = _lc.FRESH_FOR
_now = _lc._now

__all__ = [
    "CachedLicense",
    "save_cache",
    "load_cache",
    "is_fresh",
    "assert_license",
    "remote_verify",
    "CACHE_PATH",
    "FRESH_FOR",
    "_now",
]
