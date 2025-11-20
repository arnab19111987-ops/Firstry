from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from ..twin.hashers import env_fingerprint, hash_bytes, tool_version_hash
from .base import CheckRunner, RunResult, _hash_config, _hash_targets, ensure_bin

# Capture original subprocess.run so tests that monkeypatch it can be detected.
_ORIG_SUBPROCESS_RUN = subprocess.run


class PytestRunner(CheckRunner):
    check_id = "pytest"

    def prereq_check(self) -> Optional[str]:
        return ensure_bin("pytest")

    def build_cache_key(
        self, repo_root: Path, targets: List[str], flags: List[str]
    ) -> str:
        tv = tool_version_hash(["pytest", "--version"])
        env = env_fingerprint()
        tgt = _hash_targets(repo_root, targets or ["tests"])
        cfg = _hash_config(
            repo_root, ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg"]
        )
        intent = hash_bytes((" ".join(sorted(flags))).encode())
        return "ft-v1-pytest-" + hash_bytes(f"{tv}|{env}|{tgt}|{cfg}|{intent}".encode())

    def run(
        self, repo_root: Path, targets: List[str], flags: List[str], *, timeout_s: int
    ) -> RunResult:
        test_targets = targets or ["tests"]
        args = ["pytest", "-q", *test_targets, *flags]
        # Avoid launching nested pytest when we're already running under
        # the pytest test harness. If subprocess.run has been monkeypatched
        # by a test, allow the monkeypatched function to run so tests that
        # simulate pytest output continue to exercise parsing logic.
        import os

        if "PYTEST_CURRENT_TEST" in os.environ and subprocess.run is _ORIG_SUBPROCESS_RUN:
            return RunResult(status="skip", stdout="", stderr="(skipped nested pytest in test process)")
        try:
            # When running under the pytest test harness, invoking the
            # `pytest` command directly can lead to nested-run deadlocks.
            # Invoke via the current Python interpreter to ensure a fresh
            # process: `sys.executable -m pytest ...`.
            import sys

            cmd = list(args)
            if cmd and cmd[0] == "pytest":
                cmd = [sys.executable, "-m", "pytest"] + cmd[1:]

            # Ensure subprocess runs with `src` on PYTHONPATH so the child
            # process imports the repository package correctly.
            env = None
            try:
                env = dict(**__import__("os").environ)
                existing = env.get("PYTHONPATH", "")
                if "src" not in existing.split(__import__("os").pathsep):
                    env["PYTHONPATH"] = __import__("os").pathsep.join(
                        list(filter(None, ["src", existing]))
                    )
            except Exception:
                env = None

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=repo_root,
                    text=True,
                    capture_output=True,
                    timeout=timeout_s,
                    env=env,
                )
            except TypeError:
                # Monkeypatched subprocess.run may not accept env/timeout kwargs
                proc = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True)

            return RunResult(
                status="ok" if proc.returncode == 0 else "fail",
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired as e:
            return RunResult(status="error", stdout=e.stdout or "", stderr=str(e))
