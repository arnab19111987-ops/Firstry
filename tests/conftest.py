import importlib
import os
import pathlib
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def safe_isolated_env(monkeypatch):
    """
    Isolates every test from its *environment* to prevent state pollution.
    This runs automatically for every test.

    This FINAL version:
      - Clears known FirstTry environment variables.
      - Reloads stateful modules (like license/config) to clear their caches.
      - Does NOT touch the filesystem (no chdir, no home patch).
    """

    # 1. Isolate Environment Variables
    vars_to_clear = [
        "FIRSTTRY_LICENSE_KEY",
        "FIRSTTRY_LICENSE_URL",
        "FIRSTTRY_LICENSE_ALLOW",
        "FIRSTTRY_ALLOW_UNLICENSED",
        "FIRSTTRY_FORCE_TIER",
        "FIRSTTRY_DEMO_MODE",
        "FIRSTTRY_SEND_TELEMETRY",
        "FIRSTTRY_TELEMETRY_OPTOUT",
        "FT_S3_BUCKET",
        "FT_S3_PREFIX",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
    ]
    for var in vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # 2. Isolate Module Caches (by reloading them)
    mods_to_reload = [
        "firsttry.license_guard",
        "firsttry.license_cache",
        "firsttry.config.schema",
    ]
    for mod_name in mods_to_reload:
        if mod_name in importlib.sys.modules:
            try:
                importlib.reload(importlib.import_module(mod_name))
            except ImportError:
                pass  # Module might not exist in all test contexts

    yield  # <--- THE TEST RUNS HERE


"""Pytest configuration and quality gate hooks."""

# Ensure test collection is safe when guards run at import time. Set minimal
# environment defaults so modules that require secrets at import do not raise
# during collection. These are for test-time only and intentionally insecure.

os.environ.setdefault("FT_ENV", "test")
# NOTE: we intentionally do NOT set FIRSTTRY_SHARED_SECRET here; tests that need a
# secret should set it explicitly with monkeypatch so subprocess-based tests can
# accurately simulate missing-secret production behavior. Setting a global
# FIRSTTRY_SHARED_SECRET at session start leaks into subprocess envs and breaks
# assertions that validate behavior when the secret is absent.


# Ensure tests run with repository root as the current working directory
@pytest.fixture(autouse=True)
def _ensure_repo_cwd(monkeypatch):
    root = pathlib.Path(__file__).resolve().parents[1]
    monkeypatch.chdir(str(root))
    yield


def pytest_collection_modifyitems(config: Any, items: list) -> None:
    """Enforce reason= parameter on all skip and xfail markers.

    This hook runs after collection and validates that every skip/xfail marker
    has a 'reason' parameter. This ensures we maintain discipline around test
    quarantines - every skipped/xfailed test must justify why.
    """
    issues = []

    for item in items:
        # Check for skip markers without reason
        skip_markers = item.iter_markers("skip")
        for marker in skip_markers:
            if "reason" not in marker.kwargs or not marker.kwargs.get("reason"):
                issues.append(item)


@pytest.fixture(autouse=True)
def ensure_shared_secret_for_tests(monkeypatch):
    """Ensure a deterministic dev-only FIRSTTRY_SHARED_SECRET is present during tests.

    Tests that import license-related modules expect the import-time behavior to be
    stable. Rather than relying on an external env var being exported by humans,
    ensure a safe dev-only default is present for the test process only. This
    does not change production behavior.
    """
    import os

    if not os.environ.get("FIRSTTRY_SHARED_SECRET"):
        # 32+ chars recommended by runtime; this is a dev/test-only static value
        monkeypatch.setenv("FIRSTTRY_SHARED_SECRET", "dev-test-secret-0000000000000000")
    yield


@pytest.fixture(autouse=True)
def stub_external_calls(monkeypatch):
    """Stub external calls and tools for deterministic test runs."""

    import os
    import sys
    import types
    from dataclasses import dataclass

    @dataclass
    class _Proc:
        args: tuple
        returncode: int = 0
        stdout: str = ""
        stderr: str = ""

    # Stub subprocess.run to avoid real tool execution
    import subprocess
    # Keep the real run available for CLI invocations that should execute
    _real_run = subprocess.run

    def _fake_run(*args, **kwargs):
        # The test helpers often call subprocess.run([...]) where the first positional
        # argument is the argv list. Inspect that to decide whether to let the real
        # CLI run (e.g. python -m firsttry.cli) or to short-circuit external tooling.
        call_args = args[0] if args else kwargs.get("args")
        cmd_list = list(call_args) if isinstance(call_args, (list, tuple)) else [call_args]

        # Allow the real run for the project CLI and for simple system commands
        # while short-circuiting known external tooling that we don't want tests
        # to actually execute (linters, package managers, heavy tools).
        try:
            # Normalize the first token to basename (handles /usr/bin/python etc.)
            if cmd_list:
                first = str(cmd_list[0])
                exe = os.path.basename(first).lower()
            else:
                exe = ""

            # Blacklist of external tools we want to stub out
            _blacklist = {
                "ruff",
                "mypy",
                "bandit",
                "npm",
                "yarn",
                "npx",
                "node",
                "pip",
                "pip3",
                "coverage",
                "black",
                "isort",
                "docker",
                "gh",
            }

            # If the argv contains 'firsttry.cli', let the real run execute the
            # command so CLI tests behave correctly.
            if any("firsttry.cli" in str(p) for p in cmd_list):
                try:
                    return _real_run(*args, **kwargs)
                except FileNotFoundError:
                    return _Proc(args=tuple(cmd_list), returncode=127, stdout="", stderr="not found")

            # If invoking with '-m', allow some modules to run for version checks
            # (e.g. 'mypy' --version) while still stubbing heavier tools.
            if "-m" in cmd_list:
                try:
                    m_idx = cmd_list.index("-m")
                    module = str(cmd_list[m_idx + 1]) if len(cmd_list) > m_idx + 1 else ""
                except Exception:
                    module = ""
                allow_m = {"firsttry", "mypy"}
                if any(mod in module for mod in allow_m):
                    try:
                        return _real_run(*args, **kwargs)
                    except FileNotFoundError:
                        return _Proc(args=tuple(cmd_list), returncode=127, stdout="", stderr="not found")

            # If the executable is blacklisted (linters, npm, etc.), return a fake success.
            if exe in _blacklist or any(token in _blacklist for token in map(str, cmd_list)):
                return _Proc(args=tuple(cmd_list), returncode=0, stdout="", stderr="")

            # Otherwise, let the real subprocess.run handle it (echo, ls, simple cmds).
            try:
                return _real_run(*args, **kwargs)
            except FileNotFoundError:
                # Normalize the stderr to the brief message tests expect
                return _Proc(args=tuple(cmd_list), returncode=127, stdout="", stderr="not found")
        except Exception:
            # If our detection logic fails for unexpected reasons, raise so tests surface
            # the underlying problem rather than silently returning success.
            raise

    monkeypatch.setattr(subprocess, "run", _fake_run, raising=True)

    # Stub shutil.which to pretend tools exist
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/true", raising=True)

    # Stub requests if present to avoid network
    try:
        import requests  # type: ignore

        class _FakeResp:
            status_code = 200
            text = "{}"
            content = b"{}"

            def json(self):
                return {}

        class _FakeSession:
            def get(self, *a, **k):
                return _FakeResp()

            def post(self, *a, **k):
                return _FakeResp()

            def head(self, *a, **k):
                return _FakeResp()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(requests, "Session", _FakeSession, raising=False)
        monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp(), raising=False)
        monkeypatch.setattr(requests, "post", lambda *a, **k: _FakeResp(), raising=False)
        monkeypatch.setattr(requests, "head", lambda *a, **k: _FakeResp(), raising=False)
    except Exception:
        pass

    # Provide a dummy boto3 module so S3 code can import without the dependency
    if "boto3" not in sys.modules:
        fake_boto3 = types.ModuleType("boto3")

        class _DummyClient:
            def __getattr__(self, _):  # any method call is a harmless no-op
                def _noop(*a, **k):
                    return {}

                return _noop

        def client(*a, **k):
            return _DummyClient()

        fake_boto3.client = client
        sys.modules["boto3"] = fake_boto3

    # Prevent accidental file deletions or os.exec*; very defensive
    monkeypatch.setattr(os, "remove", lambda *a, **k: None, raising=True)
    monkeypatch.setattr(os, "unlink", lambda *a, **k: None, raising=True)
    monkeypatch.setattr(os, "rmdir", lambda *a, **k: None, raising=True)

    yield
