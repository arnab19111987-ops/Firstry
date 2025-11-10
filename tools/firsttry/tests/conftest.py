import sys
from pathlib import Path

# Ensure *tooling* package is first on sys.path for this test session
HERE = Path(__file__).resolve()
PKG_ROOT = HERE.parents[1]  # tools/firsttry

# Put the tooling package root (tools/firsttry) on sys.path so the inner
# `firsttry` package (tools/firsttry/firsttry) becomes the top-level module
# for the test session. This avoids the outer shim at tools/firsttry/__init__.py
# from shadowing the real tooling package.
sys.path.insert(0, str(PKG_ROOT))
