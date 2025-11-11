from __future__ import annotations

import hashlib
from pathlib import Path

from .. import cache as cache_mod
from .base import Gate, GateResult

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover - safe fallback
    tomllib = None  # type: ignore


CONFIG_CANDIDATES = [
    "ruff.toml",
    ".ruff.toml",
    "pyproject.toml",
    "pytest.ini",
    "tox.ini",
    ".flake8",
    "mypy.ini",
]


def _hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _file_hash(p: Path) -> str:
    return _hash_bytes(p.read_bytes())


def _pyproject_config_hash(p: Path) -> str:
    """Hash only config-relevant sections of pyproject.toml if possible.
    If tomllib unavailable or structure unexpected → hash whole file.
    """
    if tomllib is None:
        return _file_hash(p)

    data = tomllib.loads(p.read_text(encoding="utf-8"))
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return _file_hash(p)

    interested = {
        "ruff": tool.get("ruff"),
        "mypy": tool.get("mypy"),
        "pytest": (
            tool.get("pytest", {}).get("ini_options")
            if isinstance(tool.get("pytest"), dict)
            else None
        ),
    }

    # if nothing of interest present, hash whole file
    if not any(interested.values()):
        return _file_hash(p)

    # build a stable bytes repr
    import json

    payload = json.dumps(interested, sort_keys=True).encode("utf-8")
    return _hash_bytes(payload)


class ConfigDriftGate(Gate):
    gate_id = "config:drift"
    patterns = tuple(CONFIG_CANDIDATES)

    def run(self, root: Path) -> GateResult:
        cache = cache_mod.load_cache_legacy(root)
        prev_cfg: dict[str, str] = cache.get("config_hashes", {})

        current: dict[str, str] = {}
        changed: list[str] = []

        for name in CONFIG_CANDIDATES:
            p = root / name
            if not p.exists():
                continue

            if name == "pyproject.toml":
                h = _pyproject_config_hash(p)
            else:
                h = _file_hash(p)

            current[name] = h
            if name in prev_cfg and prev_cfg[name] != h:
                changed.append(name)

        # update cache
        cache["config_hashes"] = current
        cache_mod.save_cache_legacy(root, cache)

        if changed:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                output="Config files changed since last run:\n" + "\n".join(changed),
                watched_files=list(CONFIG_CANDIDATES),
            )

        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            output="No config drift detected (config sections).",
            watched_files=list(CONFIG_CANDIDATES),
        )
