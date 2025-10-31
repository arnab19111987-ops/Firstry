# firsttry/detectors.py
from pathlib import Path


def detect_languages(root: Path) -> set[str]:
    langs: set[str] = set()
    if (root / "pyproject.toml").exists() or list(root.rglob("*.py")):
        langs.add("python")
    if (
        (root / "package.json").exists()
        or list(root.rglob("*.js"))
        or list(root.rglob("*.ts"))
    ):
        langs.add("node")
    if (root / "go.mod").exists():
        langs.add("go")
    if (root / "Cargo.toml").exists():
        langs.add("rust")
    if (root / "Dockerfile").exists() or list(root.rglob("*.tf")):
        langs.add("infra")
    return langs


def detect_pkg_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"
