"""Compatibility shim: expose the licensing.app package as top-level `app`.

Some tests import `from app.main import app`. The actual implementation lives under
`licensing/app`. This shim re-exports the package so those imports work during tests.
"""

from importlib import import_module

# import subpackage and re-export symbols
_lic_app = import_module("licensing.app")

# Re-export any public attributes from licensing.app
for _name in getattr(_lic_app, "__all__", []) or [n for n in dir(_lic_app) if not n.startswith("_")]:
    globals()[_name] = getattr(_lic_app, _name)

__all__ = list(globals().keys())
