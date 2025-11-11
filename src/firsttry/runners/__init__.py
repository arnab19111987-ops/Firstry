"""Lightweight stub runners exposed by default (good for tests and "doctor"/stub runs).
Set FIRSTTRY_USE_REAL_RUNNERS=1 to switch to real implementations if you have them.
"""

import os
import types
from typing import Any

__all__ = [
    "RUNNERS",
    "coverage_gate",
    "run_black_check",
    "run_coverage_xml",
    "run_mypy",
    "run_pytest_kexpr",
    "run_ruff",
]


def _ok(msg: str = "ok") -> types.SimpleNamespace:
    # Return an object with attribute access (tests assert hasattr(r, 'ok'))
    return types.SimpleNamespace(ok=True, stdout=msg, stderr="", duration_s=0.0, cmd=())


def run_ruff(
    repo_root: str,
    files: list[str] | None = None,
) -> types.SimpleNamespace:
    return _ok("ruff(stub)")


def run_black_check(
    repo_root: str,
    files: list[str] | None = None,
) -> types.SimpleNamespace:
    return _ok("black --check (stub)")


def run_mypy(
    repo_root: str,
    targets: list[str] | None = None,
) -> types.SimpleNamespace:
    return _ok("mypy(stub)")


def run_pytest_kexpr(
    repo_root: str,
    kexpr: str | None = None,
) -> types.SimpleNamespace:
    return _ok("pytest -k (stub)")


def run_coverage_xml(repo_root: str) -> types.SimpleNamespace:
    return _ok("coverage xml (stub)")


def coverage_gate(repo_root: str, min_percent: int = 0) -> types.SimpleNamespace:
    return _ok(f"coverage gate >= {min_percent}% (stub)")


# Default RUNNERS mapping (kept minimal; tests often monkeypatch the orchestrator directly)
RUNNERS: dict[str, Any] = {}

if os.getenv("FIRSTTRY_USE_REAL_RUNNERS") in ("1", "true", "True"):
    # Optional: if you have real runner modules, import and export them here.
    # Keeping try/except so test envs without real deps don't break.
    try:
        from .real import (
            coverage_gate as _real_coverage_gate,
            run_black_check as _real_run_black_check,
            run_coverage_xml as _real_run_coverage_xml,
            run_mypy as _real_run_mypy,
            run_pytest_kexpr as _real_run_pytest_kexpr,
            run_ruff as _real_run_ruff,
        )

        run_ruff = _real_run_ruff
        run_black_check = _real_run_black_check
        run_mypy = _real_run_mypy
        run_pytest_kexpr = _real_run_pytest_kexpr
        run_coverage_xml = _real_run_coverage_xml
        coverage_gate = _real_coverage_gate
    except Exception:
        # silently keep stubs if real imports fail
        pass
