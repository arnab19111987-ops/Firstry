"""Shim module placed under tools/firsttry/firsttry so tests that import
from firsttry import gates can find a gates symbol.

This re-exports the canonical implementation (the package __path__ is set
up so the tools copy or the top-level shim will be used).
"""

from __future__ import annotations

import importlib.util
import sys
import os
from typing import List, Tuple

import importlib.machinery
import importlib.util
import traceback


def _locate_and_load_impl() -> object:
    """Robustly find and load the canonical gates implementation.

    Tries a few reasonable candidate locations (the tools copy and the
    top-level copy) and uses a SourceFileLoader to load the module. On
    failure it raises ImportError with diagnostics.
    """
    # find repo root by walking up for pyproject.toml (best effort)
    # prefer the highest ancestor pyproject.toml we find (so tools/* subpackages
    # with their own pyproject.toml don't mask the real repository root)
    p = os.path.abspath(os.path.dirname(__file__))
    repo_root = None
    highest_found = None
    for _ in range(12):
        candidate = os.path.join(p, "pyproject.toml")
        if os.path.exists(candidate):
            # record and keep walking to prefer the highest match
            highest_found = p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    if highest_found is not None:
        repo_root = highest_found
    else:
        # fallback to a fixed relative guess (three levels up from shim)
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )

    candidates = [
        os.path.join(repo_root, "tools", "firstry", "firsttry", "gates.py"),
        os.path.join(repo_root, "firsttry", "gates.py"),
        os.path.join(repo_root, "tools", "firsttry", "firsttry", "gates.py"),
    ]

    last_exc = None
    tried = []
    for path in candidates:
        tried.append(path)
        if not os.path.exists(path):
            continue
        try:
            loader = importlib.machinery.SourceFileLoader("firsttry._gates_impl", path)
            spec = importlib.util.spec_from_loader(loader.name, loader)
            if spec is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            # register under a private name to avoid import cycles
            sys.modules["firsttry._gates_impl"] = mod
            loader.exec_module(mod)
            return mod
        except Exception as exc:  # catch errors while loading/executing
            last_exc = exc

    # Nothing worked
    msg_lines = [
        "Could not locate or load gates implementation.",
        "Tried the following candidate paths:",
    ]
    msg_lines.extend([f" - {p}" for p in tried])
    if last_exc is not None:
        msg_lines.append("")
        msg_lines.append("Last loader exception:")
        msg_lines.append(
            "".join(
                traceback.format_exception(
                    type(last_exc), last_exc, last_exc.__traceback__
                )
            )
        )

    raise ImportError("\n".join(msg_lines))


_impl = _locate_and_load_impl()

# Expose both historical (run_pre_commit_gate/run_pre_push_gate) and
# newer (run_gate/format_summary/print_verbose) APIs. Adapt as needed.
# Prefer direct exports from the implementation when available.

# run_gate adapter: prefer impl.run_gate, else compose from run_pre_* if present
if hasattr(_impl, "run_gate"):
    run_gate = _impl.run_gate
else:

    def run_gate(which: str):
        if which == "pre-commit":
            if hasattr(_impl, "run_pre_commit_gate"):
                return _impl.run_pre_commit_gate()
            raise AttributeError("underlying gates impl has no pre-commit runner")
        if which == "pre-push":
            if hasattr(_impl, "run_pre_push_gate"):
                return _impl.run_pre_push_gate()
            # best-effort: if only pre-commit exists, return that
            if hasattr(_impl, "run_pre_commit_gate"):
                return _impl.run_pre_commit_gate()
            raise AttributeError("underlying gates impl has no pre-push runner")


# Historical convenience functions that some callers/tests use
if hasattr(_impl, "run_pre_commit_gate"):
    run_pre_commit_gate = _impl.run_pre_commit_gate
if hasattr(_impl, "run_pre_push_gate"):
    run_pre_push_gate = _impl.run_pre_push_gate

# Other helpers
format_summary = getattr(_impl, "format_summary", lambda *a, **k: "")
print_verbose = getattr(_impl, "print_verbose", lambda *a, **k: None)
PRE_COMMIT_TASKS: List[Tuple[str, object]] = getattr(_impl, "PRE_COMMIT_TASKS", [])
PRE_PUSH_TASKS: List[Tuple[str, object]] = getattr(_impl, "PRE_PUSH_TASKS", [])
GateResult = getattr(_impl, "GateResult", getattr(_impl, "GateResult", object))

__all__ = [
    "run_gate",
    "format_summary",
    "print_verbose",
    "PRE_COMMIT_TASKS",
    "PRE_PUSH_TASKS",
    "GateResult",
]
if hasattr(_impl, "run_pre_commit_gate"):
    __all__.append("run_pre_commit_gate")
if hasattr(_impl, "run_pre_push_gate"):
    __all__.append("run_pre_push_gate")
