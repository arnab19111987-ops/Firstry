import importlib
import os

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

import pathlib
from typing import Any

import pytest


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
                import os
                import pathlib
                import sys
                import types
                from dataclasses import dataclass

                import pytest

                @dataclass
                class _Proc:
                    args: tuple
                    returncode: int = 0
                    stdout: str = ""
                    stderr: str = ""

                @pytest.fixture(autouse=True)
                def sandbox_env(monkeypatch):
                    # Signal the code it's under tests (in case modules guard on this)
                    monkeypatch.setenv("FIRSTTRY_TEST_MODE", "1")
                    monkeypatch.setenv("FT_DISABLE_NETWORK", "1")
                    monkeypatch.setenv("FT_DISABLE_TELEMETRY", "1")
                    monkeypatch.setenv("NO_COLOR", "1")

                    # Ensure project src is importable even if PYTHONPATH not set
                    root = pathlib.Path(__file__).resolve().parents[1]
                    src = str(root / "src")
                    if src not in sys.path:
                        sys.path.insert(0, src)

                    yield

                @pytest.fixture(autouse=True)
                def stub_external_calls(monkeypatch):
                    # Stub subprocess.run to avoid real tool execution (ruff/mypy/pytest/bandit/npm/etc.)
                    import subprocess

                    def _fake_run(*args, **kwargs):
                        return _Proc(args=args, returncode=0, stdout="", stderr="")

                    monkeypatch.setattr(subprocess, "run", _fake_run, raising=True)

                    # Stub shutil.which to pretend tools exist, but won’t be called due to the run stub
                    import shutil

                    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/true", raising=True)

                    # Stub requests if present to avoid network; if not present, don’t force it
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
                        monkeypatch.setattr(
                            requests, "get", lambda *a, **k: _FakeResp(), raising=False
                        )
                        monkeypatch.setattr(
                            requests, "post", lambda *a, **k: _FakeResp(), raising=False
                        )
                        monkeypatch.setattr(
                            requests, "head", lambda *a, **k: _FakeResp(), raising=False
                        )
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
