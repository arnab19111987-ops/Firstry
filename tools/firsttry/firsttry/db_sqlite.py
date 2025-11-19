from __future__ import annotations

import os
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader


def _locate_and_load():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    candidates = [
        os.path.join(repo_root, "firsttry", "db_sqlite.py"),
        os.path.join(repo_root, "tools", "firstry", "firsttry", "db_sqlite.py"),
    ]
    for p in candidates:
        if not os.path.exists(p):
            continue
        loader = SourceFileLoader("firsttry._db_sqlite_impl", p)
        spec = spec_from_loader(loader.name, loader)
        mod = module_from_spec(spec)
        sys.modules[loader.name] = mod
        loader.exec_module(mod)
        return mod
    raise ImportError("Could not load db_sqlite implementation")


_impl = _locate_and_load()

run_sqlite_probe = getattr(_impl, "run_sqlite_probe")
_extract_upgrade_body = getattr(_impl, "_extract_upgrade_body", lambda s: "")

__all__ = ["run_sqlite_probe", "_extract_upgrade_body"]
