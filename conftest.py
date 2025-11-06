import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Ensure repo's src and root come first so imports resolve here, not site-packages
for p in (str(SRC), str(ROOT)):
    if p not in sys.path[:2]:
        sys.path.insert(0, p)

# --- Pin top-level `tests` as the canonical package during collection ---
TOP_TESTS = ROOT / "tests" / "__init__.py"
if TOP_TESTS.exists():
    spec = importlib.util.spec_from_file_location("tests", TOP_TESTS)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # executes tests/__init__.py
    # Ensure imports like `import tests.cli_utils` search the top-level folder
    mod.__path__ = [str(TOP_TESTS.parent)]  # type: ignore[attr-defined]
    sys.modules["tests"] = mod

# One-off debug: FT_DEBUG_IMPORTS=1 pytest -q -s
if os.environ.get("FT_DEBUG_IMPORTS"):
    import pprint

    print("\n[conftest] sys.path (first 6):")
    pprint.pp(sys.path[:6])
