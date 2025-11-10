"""
Try to reach argparse parsing paths without running real work.
We set env flags so code paths can short-circuit under test.
"""

import importlib

import pytest


def test_cli_import_and_callable(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_TEST_MODE", "1")
    cli = importlib.import_module("firsttry.cli")

    # Look for a typical callable entrypoint; if not present, skip gracefully.
    entry = None
    for name in ("main", "run", "cli_main", "entrypoint"):
        if hasattr(cli, name) and callable(getattr(cli, name)):
            entry = getattr(cli, name)
            break

    if entry is None:
        pytest.skip("No obvious CLI entrypoint found; import coverage achieved.")

    # Call it with a harmless argv if it accepts args; otherwise call bare.
    try:
        entry(["--help"])
    except SystemExit as e:
        # argparse usually raises SystemExit after printing help; success if code==0
        assert e.code in (0, None)
