"""
Thin shim package that aliases to the root-level `firsttry` package.

This ensures that imports like `import firsttry` or `from firsttry import cli`
resolve to the single, authoritative implementation under the repository root,
avoiding drift between dual package layouts.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _alias_to_root_package() -> None:
    # Compute repo root from this file: tools/firsttry/firsttry/__init__.py
    pkg_dir = Path(__file__).resolve().parent  # .../tools/firsttry/firsttry
    repo_root = pkg_dir.parents[2]  # .../ (workspace root)
    root_pkg_dir = repo_root / "firsttry"
    root_init = root_pkg_dir / "__init__.py"

    # Load the root package with proper submodule search locations so that
    # subsequent imports like `firsttry.cli` resolve under the root package.
    spec = importlib.util.spec_from_file_location(
        __name__,
        str(root_init),
        submodule_search_locations=[str(root_pkg_dir)],
    )
    # Assert for mypy: spec and loader are not None past this point
    assert spec is not None, "spec_from_file_location() returned None"
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, "spec.loader is None; cannot exec_module"
    spec.loader.exec_module(module)

    # Replace this module entry with the root package module, effectively
    # aliasing tools/firsttry/firsttry -> root/firsttry
    sys.modules[__name__] = module


_alias_to_root_package()
