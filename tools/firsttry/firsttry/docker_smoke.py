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
        os.path.join(repo_root, "firsttry", "docker_smoke.py"),
        os.path.join(repo_root, "tools", "firstry", "firsttry", "docker_smoke.py"),
    ]
    for p in candidates:
        if not os.path.exists(p):
            continue
        loader = SourceFileLoader("firsttry._docker_smoke_impl", p)
        spec = spec_from_loader(loader.name, loader)
        mod = module_from_spec(spec)
        sys.modules[loader.name] = mod
        loader.exec_module(mod)
        return mod
    raise ImportError("Could not load docker_smoke implementation")


_impl = _locate_and_load()

build_compose_cmds = getattr(_impl, "build_compose_cmds")
check_health = getattr(_impl, "check_health")
run_docker_smoke = getattr(_impl, "run_docker_smoke")

__all__ = ["build_compose_cmds", "check_health", "run_docker_smoke"]
