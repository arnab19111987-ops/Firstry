"""Cache adapters for FirstTry.

Historically `firsttry.cache` was a module (``src/firsttry/cache.py``) that
exported a set of convenience functions used by tests and legacy callers
(`load_cache`, ``save_cache``, ``should_skip_gate`` etc.). During refactors a
package was introduced at `src/firsttry/cache/` which unintentionally shadowed
the module. To maintain backward compatibility we re-export the common module
level helpers from the package root here.

The package also exposes adapter modules: ``base``, ``local``, and ``s3``.
"""

from __future__ import annotations

from importlib import util as _importlib_util
from pathlib import Path as _Path
from typing import TYPE_CHECKING

# Attempt to load the legacy module file ``src/firsttry/cache.py`` directly
# (as a separate module) and re-export its public helpers. We can't import
# "firsttry.cache" by name here because the package itself is occupying that
# import path; so load the file by path into an internal module name.
_legacy_cache = None
try:
    _root = _Path(__file__).resolve().parents[1]
    _legacy_path = _root / "cache.py"
    if _legacy_path.exists():
        _spec = _importlib_util.spec_from_file_location(
            "firsttry._legacy_cache",
            str(_legacy_path),
        )
        if _spec and _spec.loader:
            _legacy = _importlib_util.module_from_spec(_spec)
            _spec.loader.exec_module(_legacy)
            _legacy_cache = _legacy
except Exception:  # pragma: no cover - defensive fallback
    _legacy_cache = None

__all__ = ["base", "local", "s3"]

if _legacy_cache is not None:
    # Export all public names from the legacy module except those that would
    # shadow the package submodules (base/local/s3).
    for _name in dir(_legacy_cache):
        if _name.startswith("_"):
            continue
        if _name in ("base", "local", "s3"):
            continue
        try:
            globals()[_name] = getattr(_legacy_cache, _name)
            __all__.append(_name)
        except Exception:
            # best-effort export; ignore attributes that can't be bound
            pass

# Type stubs for commonly used functions from cache.py for mypy
if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path as PathType
    from typing import Any

    from ..cache_models import ToolCacheEntry

    # InputFileMeta removed - unused

    def load_cache() -> dict[str, Any]: ...
    def save_cache(data: dict[str, Any]) -> None: ...
    def load_cache_legacy(root: PathType) -> dict[str, Any]: ...
    def save_cache_legacy(root: PathType, data: dict[str, Any]) -> None: ...
    def sha256_of_paths(paths: Iterable[PathType]) -> str: ...
    def is_tool_cache_valid(repo_root: str, tool: str, input_hash: str) -> bool: ...
    def write_tool_cache(
        repo_root: str,
        tool_name: str,
        input_hash: str,
        status: str,
        extra: dict[str, Any] | None = None,
    ) -> None: ...
    def load_tool_cache_entry(repo_root: str, tool_name: str) -> ToolCacheEntry | None: ...
    def save_tool_cache_entry(repo_root: str, entry: ToolCacheEntry) -> None: ...
