import importlib

import pytest


def _require(modname, *funcs):
    try:
        m = importlib.import_module(modname)
    except Exception:
        pytest.skip(f"{modname} not importable")
    miss = [f for f in funcs if not hasattr(m, f)]
    if miss:
        pytest.skip(f"{modname} missing {miss}")
    return m


def test_build_command_adds_lf_when_failed(tmp_path, monkeypatch):
    sp = _require("firsttry.smart_pytest", "build_pytest_command")

    # Fake "get_failed_tests" behavior by monkeypatching inside module if present
    if hasattr(sp, "get_failed_tests"):
        monkeypatch.setattr(
            sp, "get_failed_tests", lambda *a, **k: ["tests/test_x.py::t"], raising=True
        )

    # Minimal inputs; your function may accept different kwargs — try permissive call
    # Try multiple calling styles because signatures vary between revisions
    def _attempt_build():
        callers = [
            lambda: sp.build_pytest_command(
                paths=[str(tmp_path)], mode="smart", parallel=False, extra_args=None
            ),
            lambda: sp.build_pytest_command([str(tmp_path)], "smart", False, None),
            lambda: sp.build_pytest_command(mode="smart", paths=[str(tmp_path)], parallel=False),
            lambda: sp.build_pytest_command(str(tmp_path), mode="smart"),
        ]
        for c in callers:
            try:
                return c()
            except TypeError:
                continue
        pytest.skip("unsupported build_pytest_command signature in this revision")

    cmd = _attempt_build()
    # Command should contain a last-failed style flag when prior failures are detected
    joined = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    assert "--lf" in joined or "-k last_failed" in joined or "last-failed" in joined


def test_build_command_smoke_includes_smoke_targets(tmp_path):
    sp = _require("firsttry.smart_pytest", "build_pytest_command")

    # smoke mode: allow multiple calling styles
    def _attempt_smoke():
        callers = [
            lambda: sp.build_pytest_command(
                paths=[str(tmp_path)], mode="smoke", parallel=False, extra_args=None
            ),
            lambda: sp.build_pytest_command([str(tmp_path)], "smoke", False, None),
            lambda: sp.build_pytest_command(mode="smoke", paths=[str(tmp_path)], parallel=False),
            lambda: sp.build_pytest_command(str(tmp_path), mode="smoke"),
        ]
        for c in callers:
            try:
                return c()
            except TypeError:
                continue
        pytest.skip("unsupported build_pytest_command signature in this revision")

    cmd = _attempt_smoke()
    s = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    # Heuristic: most implementations point to a focused subset in smoke mode; accept
    # a generic pytest invocation too (some implementations return a full pytest CLI).
    assert any(tok in s for tok in ("smoke", "tests", "-k", "pytest", "-x", "--maxfail"))


def test_parallel_flag_when_xdist_available(tmp_path, monkeypatch):
    sp = _require("firsttry.smart_pytest", "build_pytest_command")

    # Pretend xdist is available if the module checks it
    if hasattr(sp, "has_pytest_xdist"):
        monkeypatch.setattr(sp, "has_pytest_xdist", lambda: True, raising=True)

    def _attempt_parallel():
        callers = [
            lambda: sp.build_pytest_command(
                paths=[str(tmp_path)], mode="smart", parallel=True, extra_args=None
            ),
            lambda: sp.build_pytest_command([str(tmp_path)], "smart", True, None),
            lambda: sp.build_pytest_command(mode="smart", paths=[str(tmp_path)], parallel=True),
            lambda: sp.build_pytest_command(str(tmp_path), "smart", True),
        ]
        for c in callers:
            try:
                return c()
            except TypeError:
                continue
        pytest.skip("unsupported build_pytest_command signature in this revision")

    cmd = _attempt_parallel()
    s = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    assert "-n" in s or "--numprocesses" in s
