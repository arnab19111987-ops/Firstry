import importlib
import pathlib


def test_imports_tooling_package():
    # Import at test-time (not module import time) so conftest can adjust sys.path
    pkg = importlib.import_module("firsttry")
    # The __file__ should live under tools/firsttry/...
    assert "tools/firsttry" in str(pathlib.Path(pkg.__file__).as_posix())
