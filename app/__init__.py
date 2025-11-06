"""Compatibility shim: expose the licensing.app package as top-level `app`.

Some tests import `from app.main import app`. The actual implementation lives under
`licensing/app`. This shim re-exports the package so those imports work during tests.
"""

from importlib import import_module

# import subpackage and re-export symbols
_lic_app = import_module("licensing.app")

# Re-export any public attributes from licensing.app
for _name in getattr(_lic_app, "__all__", []) or [
    n for n in dir(_lic_app) if not n.startswith("_")
]:
    globals()[_name] = getattr(_lic_app, _name)

# Also expose the licensing implementation module as `app.licensing`
try:
    _licensing_mod = import_module("licensing.app.licensing")
    globals()["licensing"] = _licensing_mod
except Exception:
    # best-effort; tests that need this will fail later with a clear error
    pass

# Also expose other submodules commonly imported from `app.*`
for _sub in ("webhooks", "schemas"):
    try:
        _m = import_module(f"licensing.app.{_sub}")
        globals()[_sub] = _m
    except Exception:
        pass

__all__ = list(globals().keys())
