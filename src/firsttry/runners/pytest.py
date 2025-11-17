from __future__ import annotations

import sys
from pathlib import Path

from ..runners import run_pytest_files
from ..twin.hashers import env_fingerprint, hash_bytes, tool_version_hash

# Use private aliases exported by base to avoid import-time masking
from .base import (
    CheckRunner,
    RunResult,
    _hash_config as hash_config,
    _hash_targets as hash_targets,
    ensure_bin,
)


def build_pytest_cmd(nodeids: list[str], extra: list[str] | None = None) -> list[str]:
    """Build a pytest command using nodeids as positional args (no -k mangling).

    Returns a list suitable for subprocess.run.
    """
    extra = extra or []
    # Use the Python executable to run pytest module to ensure venv consistency
    cmd = [sys.executable, "-m", "pytest", "-q", *extra, *nodeids]
    return cmd


class PytestRunner(CheckRunner):
    check_id = "pytest"

    def prereq_check(self) -> str | None:
        return ensure_bin("pytest")

    def build_cache_key(
        self,
        repo_root: Path,
        targets: list[str],
        flags: list[str],
    ) -> str:
        tv = tool_version_hash(["pytest", "--version"])
        env = env_fingerprint()
        tgt = hash_targets(repo_root, targets or ["tests"])
        cfg = hash_config(
            repo_root,
            ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"],
        )
        intent = hash_bytes((" ".join(sorted(flags or []))).encode())
        return "ft-v1-pytest-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        flags: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        """Run pytest on a list of files with optional flags and timeout.

        This forwards to the shared runners.run_pytest_files helper so tests
        that monkeypatch subprocess.run are respected.
        """
        # `run_pytest_files` expects Iterable/Sequence arguments and returns
        # the lightweight RunResult defined in the package-level runners
        # module. Convert the returned object into the canonical
        # runners.base.RunResult dataclass so our declared return type
        # matches and mypy is satisfied.
        pkg_files = files or []
        pkg_base_args = tuple(flags or ())
        rr = run_pytest_files(pkg_files, base_args=pkg_base_args, cwd=repo_root, timeout=timeout_s)

        # Normalize fields into the base.RunResult dataclass shape.
        # Map the lightweight runner shape to the canonical dataclass used
        # across the codebase.
        rc = 0 if getattr(rr, "ok", False) else 1
        dur_s = getattr(rr, "duration_s", None)
        duration_ms = int(dur_s * 1000) if (dur_s is not None) else None
        return RunResult(
            name=getattr(rr, "name", "pytest"),
            rc=rc,
            stdout=getattr(rr, "stdout", ""),
            stderr=getattr(rr, "stderr", ""),
            duration_ms=duration_ms,
            status=getattr(rr, "status", ""),
            ok=getattr(rr, "ok", None),
            meta=getattr(rr, "meta", None),
        )
