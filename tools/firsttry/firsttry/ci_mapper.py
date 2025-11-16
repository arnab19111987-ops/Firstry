"""Proxy loader: try to prefer project's top-level firsttry.ci_mapper when available.
If not available, fall back to importing a local mapper implementation if present.
"""

from __future__ import annotations

import os
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec
from importlib.util import spec_from_loader


def _locate_and_load():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", ".."),
    )
    candidates = [
        os.path.join(repo_root, "firsttry", "ci_mapper_impl.py"),
        os.path.join(repo_root, "firsttry", "ci_mapper.py"),
        os.path.join(repo_root, "tools", "firstry", "firsttry", "ci_mapper.py"),
    ]
    last_exc = None
    for p in candidates:
        if not os.path.exists(p):
            continue
        try:
            loader = SourceFileLoader("firsttry._ci_mapper_impl", p)
            spec = spec_from_loader(loader.name, loader)
            mod = module_from_spec(spec)
            sys.modules[loader.name] = mod
            loader.exec_module(mod)
            return mod
        except Exception as exc:
            last_exc = exc
    raise ImportError("Could not load ci_mapper implementation", last_exc)


_impl = _locate_and_load()

rewrite_run_cmd = _impl.rewrite_run_cmd
build_ci_plan = _impl.build_ci_plan
check_ci_consistency = getattr(_impl, "check_ci_consistency", lambda: None)

__all__ = ["build_ci_plan", "check_ci_consistency", "rewrite_run_cmd"]
