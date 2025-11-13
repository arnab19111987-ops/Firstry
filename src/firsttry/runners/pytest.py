from __future__ import annotations

import sys
from pathlib import Path

from ..runners import run_pytest_files
from ..twin.hashers import env_fingerprint
from ..twin.hashers import hash_bytes
from ..twin.hashers import tool_version_hash

# Use private aliases exported by base to avoid import-time masking
from .base import CheckRunner
from .base import RunResult
from .base import _hash_config as hash_config
from .base import _hash_targets as hash_targets
from .base import ensure_bin


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
        # `run_pytest_files` expects `timeout` kwarg (subprocess timeout).
        return run_pytest_files(files, base_args=tuple(flags), cwd=repo_root, timeout=timeout_s)
