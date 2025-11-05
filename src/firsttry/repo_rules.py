# src/firsttry/repo_rules.py
from __future__ import annotations

import os
from typing import Any, Dict, List
from .constants import LEVELS


def _file_exists(path: str) -> bool:
    return os.path.exists(path)


def detect_features() -> Dict[str, bool]:
    return {
        "has_pyproject": _file_exists("pyproject.toml"),
        "has_requirements": _file_exists("requirements.txt"),
        "has_mypy_cfg": _file_exists("mypy.ini") or _file_exists("setup.cfg"),
        "has_pytests": _file_exists("pytest.ini") or _file_exists("conftest.py"),
        "has_package_json": _file_exists("package.json"),
        "has_tsconfig": _file_exists("tsconfig.json"),
        "has_jest": _file_exists("jest.config.js")
        or _file_exists("jest.config.cjs")
        or _file_exists("jest.config.mjs"),
        "has_vitest": _file_exists("vitest.config.ts")
        or _file_exists("vitest.config.js"),
        "has_dockerfile": _file_exists("Dockerfile"),
    }


def plan_checks_for_repo(repo_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    languages = repo_profile.get("languages", []) or []
    features = detect_features()
    plans: List[Dict[str, Any]] = []

    # Badge mapping function (use centralized labels)
    def get_badge_for_tool(tool: str) -> str:
        # map tools to level numbers
        tool_map = {
            "ruff": 1,
            "eslint": 1,
            "hadolint": 1,
            "mypy": 2,
            "tsc": 2,
            "pytest": 2,
            "npm-test": 2,
            "bandit": 2,
            "pip-audit": 2,
            "npm-audit": 2,
            "ci-parity": 3,
        }
        level = tool_map.get(tool)
        if level and level in LEVELS:
            return LEVELS[level]["label"]
        return "unknown"

    # PYTHON
    if (
        "python" in languages
        or features["has_pyproject"]
        or features["has_requirements"]
    ):
        plans.append(
            {
                "family": "lint",
                "tool": "ruff",
                "lang": "python",
                "badge": get_badge_for_tool("ruff"),
            }
        )
        if features["has_mypy_cfg"] or features["has_pyproject"]:
            plans.append(
                {"family": "type", "tool": "mypy", "badge": get_badge_for_tool("mypy")}
            )
        if repo_profile.get("test_count", 0) > 0 or features["has_pytests"]:
            plans.append(
                {
                    "family": "tests",
                    "tool": "pytest",
                    "badge": get_badge_for_tool("pytest"),
                }
            )
        plans.append(
            {
                "family": "security",
                "tool": "bandit",
                "badge": get_badge_for_tool("bandit"),
            }
        )
        if features["has_requirements"]:
            plans.append(
                {
                    "family": "deps",
                    "tool": "pip-audit",
                    "badge": get_badge_for_tool("pip-audit"),
                }
            )

    # NODE
    if features["has_package_json"]:
        plans.append(
            {
                "family": "lint",
                "tool": "eslint",
                "lang": "js",
                "badge": get_badge_for_tool("eslint"),
            }
        )
        if features["has_tsconfig"]:
            plans.append(
                {"family": "type", "tool": "tsc", "badge": get_badge_for_tool("tsc")}
            )
        if features["has_jest"] or features["has_vitest"]:
            plans.append(
                {
                    "family": "tests",
                    "tool": "npm-test",
                    "badge": get_badge_for_tool("npm-test"),
                }
            )
        plans.append(
            {
                "family": "deps",
                "tool": "npm-audit",
                "badge": get_badge_for_tool("npm-audit"),
            }
        )

    # DOCKER
    if features["has_dockerfile"]:
        plans.append(
            {
                "family": "lint",
                "tool": "hadolint",
                "lang": "docker",
                "badge": get_badge_for_tool("hadolint"),
            }
        )

    # CI parity pseudo-family
    plans.append(
        {
            "family": "ci_parity",
            "tool": "ci-parity",
            "badge": get_badge_for_tool("ci-parity"),
        }
    )

    return plans
