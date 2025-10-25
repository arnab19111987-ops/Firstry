from __future__ import annotations

import os
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec


def _locate_and_load():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    candidates = [
        os.path.join(repo_root, "firsttry", "vscode_skel.py"),
        os.path.join(repo_root, "tools", "firstry", "firsttry", "vscode_skel.py"),
    ]
    for p in candidates:
        if not os.path.exists(p):
            continue
        loader = SourceFileLoader("firsttry._vscode_skel_impl", p)
        spec = spec_from_loader(loader.name, loader)
        mod = module_from_spec(spec)
        sys.modules[loader.name] = mod
        loader.exec_module(mod)
        return mod
    raise ImportError("Could not load vscode_skel implementation")


_impl = _locate_and_load()

PACKAGE_JSON = getattr(_impl, "PACKAGE_JSON")
EXTENSION_JS = getattr(_impl, "EXTENSION_JS")

__all__ = ["PACKAGE_JSON", "EXTENSION_JS"]
