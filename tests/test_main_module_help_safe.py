"""
Some projects execute CLI on import via __main__. We execute `firsttry.__main__`
with `-h` under stubs, but guard failure so we don't break the suite if it exits.
"""

import runpy
import sys

import pytest


def test_dunder_main_help_executes_safely(monkeypatch):
    # Provide a minimal argv so if it parses it shows help and exits(0)
    monkeypatch.setenv("FIRSTTRY_TEST_MODE", "1")
    old_argv = sys.argv[:]
    try:
        sys.argv = ["firsttry", "-h"]
        # run_module will execute the module like `python -m firsttry`
        # If module calls sys.exit, allow SystemExit and assert it’s clean.
        with pytest.raises(SystemExit) as ei:
            runpy.run_module("firsttry.__main__", run_name="__main__")
        assert ei.value.code in (0, None)
    finally:
        sys.argv = old_argv
