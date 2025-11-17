from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

Language = Literal["python", "javascript", "go", "rust", "mixed", "unknown"]


@dataclass(frozen=True)
class ProjectTwin:
    root: Path
    language: Language
    detectors: Mapping[str, bool]
    packages: Mapping[str, str]
    changed_files: Sequence[Path]
    ci_hints: Mapping[str, str]


def build_twin(root: Path) -> ProjectTwin:
    """Lightweight, side-effect-free detection that never raises hard errors."""
    from .utils.fs import safe_glob

    pkg_json = (root / "package.json").exists()
    pyproject = (root / "pyproject.toml").exists()
    language: Language = "unknown"
    if pkg_json and pyproject:
        language = "mixed"
    elif pyproject:
        language = "python"
    elif pkg_json:
        language = "javascript"

    # Minimal, pluggable detectors (non-fatal)
    detectors = {
        "package_json": pkg_json,
        "pyproject": pyproject,
        "ci_github": (root / ".github" / "workflows").exists(),
    }

    packages: dict[str, str] = {}
    # Avoid heavy I/O: read only if small & present
    try:
        if pyproject:
            import tomllib

            data = tomllib.loads((root / "pyproject.toml").read_text())
            for k, v in data.get("project", {}).get("dependencies", []) or []:
                packages[k] = v
    except Exception:
        pass

    changed_files = [Path(p) for p in safe_glob(root, "**/*", max_files=300)]
    ci_hints = {"runner": "gha" if detectors["ci_github"] else "unknown"}
    return ProjectTwin(
        root=root,
        language=language,
        detectors=detectors,
        packages=packages,
        changed_files=changed_files,
        ci_hints=ci_hints,
    )
