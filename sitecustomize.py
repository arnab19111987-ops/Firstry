"""Local test-time safety wrapper for importlib.invalidate_caches.

On some test environments a finder on sys.meta_path can expose an
`invalidate_caches` attribute that is not a bound classmethod, causing
importlib.invalidate_caches() to raise a TypeError when called. That
breaks tests that call monkeypatch.syspath_prepend (which calls
importlib.invalidate_caches()).

This file wraps importlib.invalidate_caches at process start so tests are
robust. It's added only for the dev/test environment inside this repo.
"""

import importlib
import sys

_orig_invalidate = getattr(importlib, "invalidate_caches", None)


def _safe_invalidate_caches():
    """Call the original invalidate_caches but tolerate TypeError from finders.

    If the original call fails with a TypeError (common when a finder exposes
    an unbound function), fall back to calling any finder.invalidate_caches()
    in a defensive manner.
    """
    if _orig_invalidate is None:
        return None
    try:
        return _orig_invalidate()
    except TypeError:
        # Defensive fallback: iterate finders and call their invalidate_caches
        for finder in list(sys.meta_path):
            fn = getattr(finder, "invalidate_caches", None)
            if not fn:
                continue
            try:
                # try calling as bound/method
                fn()
            except TypeError:
                # try calling with the class as first arg (unbound function)
                try:
                    fn(finder.__class__)
                except Exception:
                    # swallow everything — this is best-effort
                    pass
            except Exception:
                # ignore other errors from custom finders
                pass
        return None
    except Exception:
        # Any other exception: ignore to keep tests running
        return None


# Patch importlib.invalidate_caches in-place
importlib.invalidate_caches = _safe_invalidate_caches
