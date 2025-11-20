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
from typing import TYPE_CHECKING, Any

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
            "firsttry._legacy_cache", str(_legacy_path)
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

    # Some legacy helpers consult module-level `CACHE_FILE`. Tests commonly
    # monkeypatch `firsttry.cache.CACHE_FILE` (the package attribute). To make
    # that work when callers invoke functions we wrap `load_cache` and
    # `save_cache` to synchronize the legacy module's `CACHE_FILE` with the
    # package-level value before delegating. This keeps behavior compatible
    # while allowing tests to monkeypatch the exported name.
    def _sync_cache_file():
        pkg_val = globals().get("CACHE_FILE", None)
        try:
            setattr(_legacy_cache, "CACHE_FILE", pkg_val)
        except Exception:
            pass

    if hasattr(_legacy_cache, "load_cache"):
        _orig_load = _legacy_cache.load_cache

        def load_cache(*a: Any, **k: Any) -> dict[str, Any]:
            _sync_cache_file()
            return _orig_load(*a, **k)

        globals()["load_cache"] = load_cache
        __all__.append("load_cache")

    if hasattr(_legacy_cache, "save_cache"):
        _orig_save = _legacy_cache.save_cache

        def save_cache(*a: Any, **k: Any) -> None:
            _sync_cache_file()
            return _orig_save(*a, **k)

        globals()["save_cache"] = save_cache
        __all__.append("save_cache")

if TYPE_CHECKING:
    # Provide typing-only declarations for the names re-exported at runtime
    # so static analyzers (mypy) can see these attributes on the
    # `firsttry.cache` package without relying on the dynamic import logic
    # above. These declarations do not affect runtime behavior.
    from pathlib import Path
    from typing import Any, Dict, Iterable, Optional, Tuple

    CACHE_FILE: Optional[Path]

    def sha256_of_paths(paths: Iterable[Path]) -> str: ...

    def load_cache(*a: Any, **k: Any) -> Dict[str, Any]: ...

    def save_cache(*a: Any, **k: Any) -> None: ...

    def load_tool_cache_entry(repo_root: str, tool_name: str) -> Optional[Any]: ...

    def save_tool_cache_entry(repo_root: str, entry: Any) -> None: ...

    def is_tool_cache_valid(
        repo_root: str, tool_name: str, input_hash: str
    ) -> bool: ...

    def write_tool_cache(
        repo_root: str,
        tool_name: str,
        input_hash: str,
        status: str,
        extra: Dict[str, Any] | None = None,
    ) -> None: ...

    def is_tool_cache_valid_fast(
        repo_root: str, tool_name: str, input_paths: list[str]
    ) -> Tuple[bool, str]: ...

    def invalidate_tool_cache(repo_root: str, tool_name: str) -> None: ...

    def load_cache_legacy(root: Path) -> Dict[str, Any]: ...

    def save_cache_legacy(root: Path, data: Dict[str, Any]) -> None: ...

    def should_skip_gate(
        cache: dict, gate_id: str, changed_files: list[str]
    ) -> bool: ...

    def update_gate_cache(
        cache: dict, gate_id: str, watched_files: list[str]
    ) -> None: ...
