# src/firsttry/context_builders.py
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List


def _detect_repo_root() -> str:
    return str(Path(".").resolve())


def _list_py_files(repo_root: str | None = None) -> List[str]:
    root = Path(repo_root or ".")
    out: List[str] = []
    for p in root.rglob("*.py"):
        # skip venv/.git
        if ".venv" in p.parts or "venv" in p.parts or ".git" in p.parts:
            continue
        out.append(str(p))
    return out


CONFIG_FILES = [
    "pyproject.toml",
    "firsttry.toml",
    "setup.cfg",
    "mypy.ini",
    "pytest.ini",
    ".flake8",
    ".ruff.toml",
    ".pre-commit-config.yaml",
]


def build_context() -> Dict[str, Any]:
    """
    Context = machine + repo_root
    """
    repo_root = _detect_repo_root()
    return {
        "repo_root": repo_root,
        "machine": {
            "os": os.uname().sysname.lower(),
            "cpus": os.cpu_count() or 1,
        },
    }


def build_repo_profile() -> Dict[str, Any]:
    """
    Basic repo facts for planner/agent-manager.
    """
    repo_root = _detect_repo_root()
    py_files = _list_py_files(repo_root)
    test_count = sum(
        1
        for f in py_files
        if "/tests/" in f or f.endswith("_test.py") or f.startswith("tests/")
    )
    return {
        "repo_root": repo_root,
        "file_count": len(py_files),
        "test_count": test_count,
        "languages": ["python"] if py_files else [],
    }


def compute_config_hashes(root: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name in CONFIG_FILES:
        path = Path(root) / name
        if not path.exists():
            continue
        data = path.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        out[name] = h
    return out
