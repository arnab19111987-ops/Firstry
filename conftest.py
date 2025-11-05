import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Ensure repo's src and root come first so imports resolve here, not site-packages
for p in (str(SRC), str(ROOT)):
    if p not in sys.path[:2]:
        sys.path.insert(0, p)

# One-off debug: FT_DEBUG_IMPORTS=1 pytest -q -s
if os.environ.get("FT_DEBUG_IMPORTS"):
    import pprint

    print("\n[conftest] sys.path (first 6):")
    pprint.pp(sys.path[:6])
