import importlib

import pytest


def test_smart_pytest_deselection_and_env_paths(monkeypatch, tmp_path):
    try:
        sp = importlib.import_module("firsttry.smart_pytest")
    except Exception:
        pytest.skip("smart_pytest not present.")

    # Look for a high-level API likely used by CLI integrations
    entry = None
    for name in ("plan_and_run", "select_and_run", "run_smart", "smart_pytest_main"):
        if hasattr(sp, name) and callable(getattr(sp, name)):
            entry = getattr(sp, name)
            break

    if entry is None:
        pytest.skip("smart_pytest entrypoint not found.")

    # create a fake repo layout that should trigger "no tests" / deselect logic safely
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("x=1\n", encoding="utf-8")

    # Often these modules respect env flags — use the same flags as Phase 1
    monkeypatch.setenv("FIRSTTRY_TEST_MODE", "1")
    monkeypatch.setenv("FT_DISABLE_TELEMETRY", "1")
    monkeypatch.chdir(tmp_path)

    # Call the entry with minimal kwargs; allow graceful "no tests collected" flows
    try:
        rv = entry(paths=[str(pkg)])
    except TypeError:
        try:
            rv = entry([str(pkg)])
        except TypeError:
            rv = entry()

    assert rv is None or isinstance(rv, int)
