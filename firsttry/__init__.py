from __future__ import annotations

__all__ = [
    "db_sqlite",
    "ci_mapper",
    "cli",
    "db_pg",
    "docker_smoke",
    "gates",
    "vscode_skel",
]

__version__ = "0.1.0"

# If a sibling tools/firstry/firsttry package exists (used by our tools layout),
# prefer its modules for submodule imports by adding it to this package's
# __path__. This makes `import firsttry.db_pg` resolve to
# tools/firstry/firsttry/db_pg.py when present.
import os

_here = os.path.dirname(__file__)
_repo_root = os.path.dirname(_here)
_alt = os.path.join(_repo_root, "tools", "firstry", "firsttry")
if os.path.isdir(_alt):
    # insert at front so the tools package wins over other locations
    __path__.insert(0, _alt)
