# firsttry/detect.py
from pathlib import Path

PYTHON_MARKERS = ("pyproject.toml", "requirements.txt", "setup.cfg", "setup.py")
NODE_MARKERS = ("package.json",)
GO_MARKERS = ("go.mod",)
SHELL_MARKERS = (
    ".envrc",
    "scripts",
)


def detect_language(cwd: str | None = None) -> list[str]:
    """Return a list of stacks present in this repo: ['python', 'node', 'go', ...]."""
    root = Path(cwd or ".")
    langs: list[str] = []

    if any((root / m).exists() for m in PYTHON_MARKERS):
        langs.append("python")
    if any((root / m).exists() for m in NODE_MARKERS):
        langs.append("node")
    if any((root / m).exists() for m in GO_MARKERS):
        langs.append("go")
    # shell is optional – detect if there's a scripts dir or shell files
    shell_files = list(root.glob("*.sh")) + list(root.glob("scripts/*.sh"))
    if shell_files:
        langs.append("shell")

    if not langs:
        return ["unknown"]
    return langs


def deps_for_stacks(stacks: list[str]) -> dict[str, list[str]]:
    """
    For each detected stack, return the tools we want.
    We'll only *print* these; actual installation is up to the user/env.
    """
    deps: dict[str, list[str]] = {}
    if "python" in stacks:
        # Autofix-first tools, then detect-only
        deps["python"] = [
            "black",
            "isort",
            "ruff",
            "mypy",  # detect-only
            "pytest",  # detect-only
            "bandit",  # detect-only
        ]
    if "node" in stacks:
        deps["node"] = [
            "eslint",
            "prettier",
        ]
    if "shell" in stacks:
        deps["shell"] = [
            "shfmt",
            "shellcheck",
        ]
    return deps
