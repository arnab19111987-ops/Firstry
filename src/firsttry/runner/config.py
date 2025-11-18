"""Configuration loader with tomllib (Python 3.11+) and tomli fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

from firsttry.tests.prune import get_changed_files, select_impacted_tests

from .planner import Planner


def build_pytest_cmd(prune: bool = False) -> tuple[List[str], dict]:
    """Build pytest command, optionally injecting pruned nodeids.

    If pruning is requested, attempt to select impacted nodeids via git changes
    and the test index. Falls back to full pytest command on errors or empty
    selection.

    Returns:
        Tuple of (cmd_list, metadata_dict) where metadata includes prune_enabled and nodeids_selected
    """
    base = ["pytest", "-q"]
    meta = {"prune_enabled": bool(prune), "nodeids_selected": 0, "test_files_selected": 0}
    if not prune:
        return base, meta
    try:
        changed = get_changed_files()
        nodeids = select_impacted_tests(changed)
        if nodeids:
            meta["nodeids_selected"] = len(nodeids)
            return base + nodeids, meta
        # Fallback: if test files changed, pass file paths to pytest to run just those files
        test_files = [f for f in changed if f.startswith("tests/") and f.endswith(".py")]
        if test_files:
            meta["test_files_selected"] = len(test_files)
            return base + test_files, meta
        return base, meta
    except Exception:
        return base, meta


def load_graph_from_config(config_path: str | Path, prune_tests: bool = False):
    """Build a DAG from the TOML config, wiring pytest cmd for pruning.

    Args:
        config_path: Path to TOML config
        prune_tests: If True, attempt to inject pruned pytest nodeids

    Returns:
        Tuple of (DAG, prune_metadata_dict)
    """
    cfg = {}
    try:
        cfg = ConfigLoader.load(config_path)
    except Exception:
        cfg = {}

    workflow = cfg.get("workflow", {})
    # Build pytest cmd according to prune flag
    pytest_cmd, prune_meta = build_pytest_cmd(prune_tests)
    workflow["pytest_cmd"] = pytest_cmd

    planner = Planner()
    # If config file exists on disk, prefer planner cache
    conf_path_str = str(config_path)
    try:
        if Path(conf_path_str).exists():
            # If pruning requested, avoid cached plan because cached plan
            # may not include pruned pytest nodeids. Build a fresh DAG.
            if prune_tests:
                return planner.build_dag(workflow, Path(".")), prune_meta
            return planner.get_cached_dag(conf_path_str, workflow, Path(".")), prune_meta
    except Exception:
        pass

    return planner.build_dag(workflow, Path(".")), prune_meta


# Use tomllib for Python 3.11+, fall back to tomli for earlier versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


class ConfigLoader:
    """Load FirstTry configuration from TOML files."""

    @staticmethod
    def load(config_path: Path | str) -> Dict[str, Any]:
        """Load configuration from a TOML file.

        Args:
            config_path: Path to TOML configuration file

        Returns:
            Configuration dictionary

        Raises:
            RuntimeError: If tomllib/tomli not available
            FileNotFoundError: If config file not found
            ValueError: If TOML parsing fails
        """
        if tomllib is None:
            raise RuntimeError("TOML library not available. Install 'tomli' for Python < 3.11.")

        config_path_obj = Path(config_path) if isinstance(config_path, str) else config_path

        if not config_path_obj.exists():
            raise FileNotFoundError(f"Config file not found: {config_path_obj}")

        try:
            with open(config_path_obj, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse TOML file {config_path_obj}: {e}") from e

    @staticmethod
    def load_workflow(config_path: Path | str) -> Dict[str, Any]:
        """Load workflow configuration.

        Args:
            config_path: Path to TOML configuration file

        Returns:
            Workflow section from config
        """
        config = ConfigLoader.load(config_path)
        return config.get("workflow", {})

    @staticmethod
    def load_resources(config_path: Path | str) -> Dict[str, Any]:
        """Load resources configuration.

        Args:
            config_path: Path to TOML configuration file

        Returns:
            Resources section from config
        """
        config = ConfigLoader.load(config_path)
        return config.get("resources", {})
