from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Callable

import firsttry._config_module as legacy_mod
import firsttry._original_config as original_mod
import firsttry.config as pkg_config
import firsttry.config._core as core_config


def _call_get_config(fn: Callable[[Path | None], Any]) -> dict[str, Any]:
    """Call a get_config-like function and normalize to raw dict.

    We assume the new core returns a Config dataclass with a .raw mapping.
    Legacy shims should return that same Config instance.
    """
    cfg = fn(None)  # new core supports root=None meaning cwd
    # Be liberal: accept either Config object with .raw or plain dict.
    if hasattr(cfg, "raw"):
        return dict(cfg.raw)
    if isinstance(cfg, dict):
        return dict(cfg)
    raise TypeError(f"Unsupported config object type: {type(cfg)!r}")


def test_all_get_config_entrypoints_share_same_impl(tmp_path, monkeypatch) -> None:
    """All public get_config entrypoints should be thin wrappers around the core.

    This guards against accidental reintroduction of duplicate loaders.
    """

    # Force a known minimal config layout by creating a temp firsttry.toml
    monkeypatch.chdir(tmp_path)
    (Path("firsttry.toml")).write_text("[cache]\nlocal = true\nremote = false\n", encoding="utf-8")

    # Collect entrypoints
    entrypoints = {
        "core": core_config.get_config,
        "pkg": pkg_config.get_config,
        "legacy_mod": legacy_mod.get_config,
        "original_mod": original_mod.get_config,
    }

    raw_by_name: dict[str, dict[str, Any]] = {}
    for name, fn in entrypoints.items():
        raw_by_name[name] = _call_get_config(fn)

    # All raw dicts must be equal
    core_raw = raw_by_name["core"]
    for name, raw in raw_by_name.items():
        assert raw == core_raw, f"get_config from {name} diverged from core implementation"


def test_config_module_objects_are_shims_not_new_implementations() -> None:
    """Sanity check: legacy modules only re-export, they don't hold their own logic."""

    # The modules themselves should be imported modules, not separate copies of core.
    assert isinstance(legacy_mod, types.ModuleType)
    assert isinstance(original_mod, types.ModuleType)

    # Their get_config functions should be the same object as the package-level one,
    # or at least the same function wrapper (e.g., alias).
    assert legacy_mod.get_config is pkg_config.get_config
    assert original_mod.get_config is pkg_config.get_config
