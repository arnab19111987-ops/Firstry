import io
import runpy
import sys

from firsttry import __version__


def test_module_dunder_main_version(monkeypatch):
    # Simulate: python -m firsttry version
    monkeypatch.setattr(sys, "argv", ["firsttry", "version"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    try:
        # Execute the package entrypoint module, equivalent to `python -m firsttry`
        runpy.run_module("firsttry.__main__", run_name="__main__")
    except SystemExit as e:
        # click exits with 0 on --version
        assert int(e.code) == 0

    out = buf.getvalue()
    # Click prints just version string when using --version
    assert __version__ in out
