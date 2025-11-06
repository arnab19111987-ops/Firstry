"""Shim module re-exporting licensing.app.webhooks as app.webhooks for tests."""

from importlib import import_module

_m = import_module("licensing.app.webhooks")

# Re-export public names
for _n in getattr(_m, "__all__", []) or [n for n in dir(_m) if not n.startswith("_")]:
    globals()[_n] = getattr(_m, _n)

__all__ = list(globals().keys())
