from __future__ import annotations

import pathlib
import sys
from io import StringIO

from firsttry.gates.deps import suggest_dependency_fix


def test_dependency_advisor_suggests_for_missing_module(tmp_path: pathlib.Path) -> None:
    pyproj = """
    [project]
    name = "demo"
    version = "0.0.1"
    dependencies = [
        "requests>=2.0",
    ]
    """
    (tmp_path / "pyproject.toml").write_text(pyproj, encoding="utf8")

    stderr = "Traceback...\nModuleNotFoundError: No module named 'blake3'\n"
    cmd = "python -m firsttry.cli run --tier lite"

    buf = StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        suggest_dependency_fix(root=tmp_path, stderr=stderr, cmd=cmd)
    finally:
        sys.stdout = old

    out = buf.getvalue()
    assert "Dependency advisory" in out
    assert "blake3" in out
    assert "pyproject.toml" in out
