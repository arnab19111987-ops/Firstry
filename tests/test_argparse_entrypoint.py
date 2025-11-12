from __future__ import annotations

import io
import sys

from firsttry import __version__, cli as cli_mod


def test_argparse_main_version(monkeypatch):
    # Simulate: python -m firsttry.cli version
    monkeypatch.setattr(
        sys,
        "argv",
        ["python -m firsttry.cli", "version"],
    )
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)

    rc = cli_mod.main()
    out = buf.getvalue().strip()

    assert rc == 0
    assert __version__ in out
    assert out.startswith("FirstTry ")
