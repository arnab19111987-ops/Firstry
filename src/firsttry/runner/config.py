"""Configuration loader with tomllib (Python 3.11+) and tomli fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from typing import Dict

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
