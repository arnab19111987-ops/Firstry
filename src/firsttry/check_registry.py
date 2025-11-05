from __future__ import annotations
from typing import Dict, Any, List

# Single source of truth for check definitions
CHECK_REGISTRY: Dict[str, Dict[str, Any]] = {
    # FAST checks - quick static analysis
    "ruff": {
        "bucket": "fast",
        "mutates": False,
        "inputs": ["**/*.py", "pyproject.toml", "ruff.toml", ".ruff.toml"],
    },
    "repo_sanity": {
        "bucket": "fast",
        "mutates": False,
        "inputs": ["pyproject.toml", "setup.py", "requirements*.txt", "README*"],
    },
    # MUTATING checks - modify files, must run serially
    "black": {
        "bucket": "mutating",
        "mutates": True,
        "inputs": ["**/*.py", "pyproject.toml", "black.toml", ".black.toml"],
    },
    # SLOW checks - comprehensive analysis
    "mypy": {
        "bucket": "slow",
        "mutates": False,
        "inputs": ["**/*.py", "pyproject.toml", "mypy.ini", ".mypy.ini"],
    },
    "pytest": {
        "bucket": "slow",
        "mutates": False,
        "inputs": [
            "tests/**/*.py",
            "src/**/*.py",
            "test/**/*.py",
            "**/*test*.py",
            "pyproject.toml",
            "pytest.ini",
        ],
    },
    "npm test": {
        "bucket": "slow",
        "mutates": False,
        "inputs": [
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "bun.lockb",
            "tsconfig.json",
            "jsconfig.json",
            "webpack.config.*",
            "vite.config.*",
            "rollup.config.*",
            "babel.config.*",
            ".babelrc*",
            "jest.config.*",
            "vitest.config.*",
            "playwright.config.*",
            "cypress.config.*",
            "**/*.js",
            "**/*.jsx",
            "**/*.ts",
            "**/*.tsx",
            "**/*.mjs",
            "**/*.cjs",
            "**/*.vue",
            "**/*.svelte",
            "**/*.astro",
        ],
    },
    "ci-parity": {
        "bucket": "slow",
        "mutates": False,
        "inputs": [
            ".github/workflows/**/*.yml",
            ".github/workflows/**/*.yaml",
            "firsttry.toml",
            ".firsttry.toml",
        ],
    },
}


def get_checks_for_bucket(bucket: str) -> List[str]:
    """Get all check names for a specific bucket"""
    return [name for name, meta in CHECK_REGISTRY.items() if meta["bucket"] == bucket]


def all_checks() -> List[str]:
    """Get all available check names"""
    return list(CHECK_REGISTRY.keys())


def get_check_info(check_name: str) -> Dict[str, Any]:
    """Get metadata for a specific check"""
    return CHECK_REGISTRY.get(check_name, {})


def is_check_mutating(check_name: str) -> bool:
    """Check if a tool modifies files"""
    return CHECK_REGISTRY.get(check_name, {}).get("mutates", False)


def get_check_inputs(check_name: str) -> List[str]:
    """Get input file patterns for a check"""
    return CHECK_REGISTRY.get(check_name, {}).get("inputs", [])
