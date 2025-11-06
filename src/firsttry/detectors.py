from __future__ import annotations

from pathlib import Path
from typing import Any

from .detection_cache import load_detect_cache
from .detection_cache import save_detect_cache


def detect_languages(root: Path) -> set[str]:
    """Legacy function for backward compatibility."""
    result = detect_stack(root)
    langs: set[str] = set()
    if result.get("python"):
        langs.add("python")
    if result.get("node"):
        langs.add("node")
    if result.get("go"):
        langs.add("go")
    if result.get("infra"):
        langs.add("infra")
    return langs


def _real_detect_stack(repo_root: Path) -> dict[str, Any]:
    """Fast detection logic using sentinel files first.
    This replaces expensive rglob operations with cheap file existence checks.
    """
    payload: dict[str, Any] = {
        "python": False,
        "node": False,
        "go": False,
        "infra": False,
    }

    # Fast sentinel file checks first
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.cfg").exists():
        payload["python"] = True

    if (repo_root / "package.json").exists():
        payload["node"] = True

    if (repo_root / "go.mod").exists():
        payload["go"] = True

    if (repo_root / "Cargo.toml").exists():
        payload["rust"] = True

    if (repo_root / "Dockerfile").exists():
        payload["infra"] = True

    # Only do expensive rglob if sentinel files not found
    if not payload["python"]:
        if list(repo_root.rglob("*.py")):
            payload["python"] = True

    if not payload["node"]:
        if list(repo_root.rglob("*.js")) or list(repo_root.rglob("*.ts")):
            payload["node"] = True

    if not payload["infra"]:
        if list(repo_root.rglob("*.tf")):
            payload["infra"] = True

    return payload


def detect_stack(repo_root: Path) -> dict[str, Any]:
    """Cached detect with 10-minute TTL."""
    cached = load_detect_cache(repo_root)
    if cached:
        return cached

    payload = _real_detect_stack(repo_root)
    save_detect_cache(repo_root, payload)
    return payload


def detect_pkg_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"
