# src/firsttry/deps.py
from __future__ import annotations

from pathlib import Path
from typing import Dict

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except Exception:
        tomllib = None  # type: ignore


def _read_requirements_txt(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            name, ver = line.split("==", 1)
            out[name.strip()] = ver.strip()
        else:
            out[line] = "*"
    return out


def _read_pyproject_toml(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists() or tomllib is None:
        return out
    data = tomllib.loads(path.read_text())

    proj = data.get("project") or {}
    for dep in proj.get("dependencies") or []:
        name = dep.split(";", 1)[0].strip()
        out[name] = "*"

    tool = data.get("tool") or {}
    poetry = tool.get("poetry") or {}
    poetry_deps = poetry.get("dependencies") or {}
    for name, spec in poetry_deps.items():
        if name == "python":
            continue
        if isinstance(spec, str):
            out[name] = spec
        elif isinstance(spec, dict):
            out[name] = spec.get("version", "*")
        else:
            out[name] = "*"

    return out


def _read_pipfile(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists() or tomllib is None:
        return out
    data = tomllib.loads(path.read_text())
    for section in ("packages", "dev-packages"):
        sec = data.get(section) or {}
        for name, val in sec.items():
            if isinstance(val, str):
                out[name] = val
            elif isinstance(val, dict):
                out[name] = val.get("version", "*")
            else:
                out[name] = "*"
    return out


def read_local_deps(repo_root: str) -> Dict[str, str]:
    root = Path(repo_root)
    deps: Dict[str, str] = {}
    deps.update(_read_pyproject_toml(root / "pyproject.toml"))
    deps.update(_read_pipfile(root / "Pipfile"))
    deps.update(_read_requirements_txt(root / "requirements.txt"))
    return deps
