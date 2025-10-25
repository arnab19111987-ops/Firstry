from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


_DEFAULTS = {
    "coverage_threshold": 80,
    "pytest_smoke_expr": "not slow and not integration",
    "pytest_base_args": ["-q"],
    "map_dirs": ["tools/firsttry/firsttry", "tools/firsttry/tests"],
}


@dataclass(frozen=True)
class FirstTryConfig:
    coverage_threshold: int
    pytest_smoke_expr: str
    pytest_base_args: tuple[str, ...]
    map_dirs: tuple[str, ...]

    @staticmethod
    def load(path: Optional[Path] = None) -> "FirstTryConfig":
        cfg_path = (path or Path.cwd()) / ".firsttry.yml"
        data: Dict[str, Any] = {}
        if cfg_path.exists():
            with cfg_path.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                if not isinstance(loaded, dict):
                    raise ValueError(".firsttry.yml must be a YAML mapping")
                data = loaded
        merged = {**_DEFAULTS, **data}
        return FirstTryConfig(
            coverage_threshold=int(merged["coverage_threshold"]),
            pytest_smoke_expr=str(merged["pytest_smoke_expr"]),
            pytest_base_args=tuple(merged["pytest_base_args"]),
            map_dirs=tuple(merged["map_dirs"]),
        )
