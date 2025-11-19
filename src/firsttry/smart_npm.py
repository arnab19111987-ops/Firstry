from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Set

from . import cache as ft_cache


def detect_js_project_type(repo_root: str) -> Dict[str, Any]:
    """Detect JavaScript/Node.js project type and configuration"""
    repo_path = Path(repo_root)

    # Check for common JS project files
    project_files = {
        "package.json": repo_path / "package.json",
        "package-lock.json": repo_path / "package-lock.json",
        "yarn.lock": repo_path / "yarn.lock",
        "pnpm-lock.yaml": repo_path / "pnpm-lock.yaml",
        "bun.lockb": repo_path / "bun.lockb",
        "tsconfig.json": repo_path / "tsconfig.json",
        "jsconfig.json": repo_path / "jsconfig.json",
    }

    found_files = {}
    for name, path in project_files.items():
        if path.exists():
            found_files[name] = str(path)

    # Determine package manager
    package_manager = "npm"  # default
    if "yarn.lock" in found_files:
        package_manager = "yarn"
    elif "pnpm-lock.yaml" in found_files:
        package_manager = "pnpm"
    elif "bun.lockb" in found_files:
        package_manager = "bun"

    # Parse package.json if available
    package_json_info = {}
    if "package.json" in found_files:
        try:
            with open(found_files["package.json"], "r") as f:
                package_json_info = json.load(f)
        except Exception:
            package_json_info = {}

    # Check for test scripts
    scripts = package_json_info.get("scripts", {})
    has_test_script = "test" in scripts
    test_command = scripts.get("test", "")

    # Detect test frameworks
    deps = {
        **package_json_info.get("dependencies", {}),
        **package_json_info.get("devDependencies", {}),
    }
    test_frameworks = []

    framework_patterns = {
        "jest": ["jest", "@jest/"],
        "vitest": ["vitest"],
        "mocha": ["mocha"],
        "jasmine": ["jasmine"],
        "cypress": ["cypress"],
        "playwright": ["playwright", "@playwright/"],
        "puppeteer": ["puppeteer"],
    }

    for framework, patterns in framework_patterns.items():
        if any(pattern in dep for dep in deps.keys() for pattern in patterns):
            test_frameworks.append(framework)

    return {
        "is_js_project": len(found_files) > 0,
        "package_manager": package_manager,
        "project_files": found_files,
        "has_test_script": has_test_script,
        "test_command": test_command,
        "test_frameworks": test_frameworks,
        "dependencies": deps,
        "package_json": package_json_info,
    }


def get_js_related_files(repo_root: str, changed_files: List[str] = None) -> Set[str]:
    """Get JavaScript/TypeScript related files from changed files or discover all"""
    repo_path = Path(repo_root)
    js_files = set()

    # JS/TS file extensions
    js_extensions = {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".vue",
        ".svelte",
        ".astro",
    }

    # Config file patterns that affect JS builds
    js_config_patterns = {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
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
        "eslint.config.*",
        ".eslintrc*",
        "prettier.config.*",
        ".prettierrc*",
    }

    if changed_files:
        # Filter changed files to JS-related ones
        for file_path in changed_files:
            path = Path(file_path)

            # Check extension
            if path.suffix in js_extensions:
                js_files.add(file_path)
                continue

            # Check config patterns
            filename = path.name
            if any(
                filename == pattern
                or (pattern.endswith("*") and filename.startswith(pattern[:-1]))
                for pattern in js_config_patterns
            ):
                js_files.add(file_path)
                continue
    else:
        # Discover all JS files in common directories
        js_dirs = [
            "src",
            "lib",
            "app",
            "pages",
            "components",
            "test",
            "tests",
            "__tests__",
        ]

        for js_dir in js_dirs:
            dir_path = repo_path / js_dir
            if dir_path.exists():
                for ext in js_extensions:
                    js_files.update(
                        str(f.relative_to(repo_path)) for f in dir_path.rglob(f"*{ext}")
                    )

        # Add config files
        for pattern in js_config_patterns:
            if not pattern.endswith("*"):
                config_file = repo_path / pattern
                if config_file.exists():
                    js_files.add(pattern)

    return js_files


def should_skip_npm_tests(
    repo_root: str, changed_files: List[str] = None, force_run: bool = False
) -> Dict[str, Any]:
    """
    Determine if npm tests should be skipped based on changed files and project state.
    Returns decision info and reasoning.
    """

    if force_run:
        return {
            "should_skip": False,
            "reason": "Manual override: --run-npm-anyway flag used",
            "js_files_changed": 0,
            "relevant_changes": [],
        }

    # Detect project type
    project_info = detect_js_project_type(repo_root)

    if not project_info["is_js_project"]:
        return {
            "should_skip": True,
            "reason": "No JavaScript project detected (no package.json, tsconfig.json, etc.)",
            "js_files_changed": 0,
            "relevant_changes": [],
        }

    if not project_info["has_test_script"]:
        return {
            "should_skip": True,
            "reason": "No 'test' script found in package.json",
            "js_files_changed": 0,
            "relevant_changes": [],
        }

    # If no changed files provided, assume we should run (full mode)
    if not changed_files:
        return {
            "should_skip": False,
            "reason": "Full mode: no changed files filter provided",
            "js_files_changed": "all",
            "relevant_changes": [],
        }

    # Check for JS-related changes
    js_related_changes = get_js_related_files(repo_root, changed_files)

    if not js_related_changes:
        return {
            "should_skip": True,
            "reason": f"No JavaScript/TypeScript files changed (checked {len(changed_files)} files)",
            "js_files_changed": 0,
            "relevant_changes": [],
        }

    return {
        "should_skip": False,
        "reason": f"JavaScript/TypeScript changes detected: {len(js_related_changes)} relevant files",
        "js_files_changed": len(js_related_changes),
        "relevant_changes": sorted(list(js_related_changes)),
    }


def get_npm_test_command(repo_root: str) -> List[str]:
    """Get the appropriate npm test command based on project configuration"""
    project_info = detect_js_project_type(repo_root)

    package_manager = project_info["package_manager"]

    # Build command based on package manager
    if package_manager == "yarn":
        return ["yarn", "test"]
    elif package_manager == "pnpm":
        return ["pnpm", "test"]
    elif package_manager == "bun":
        return ["bun", "test"]
    else:
        return ["npm", "test"]


async def run_smart_npm_test(
    repo_root: str,
    changed_files: List[str] = None,
    force_run: bool = False,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Run npm tests with intelligent skipping based on changes.
    Mirrors the smart pytest patterns.
    """

    # Check if we should skip
    skip_decision = should_skip_npm_tests(repo_root, changed_files, force_run)

    if skip_decision["should_skip"]:
        return {
            "status": "skipped",
            "reason": skip_decision["reason"],
            "duration": 0,
            "js_files_changed": skip_decision["js_files_changed"],
            "relevant_changes": skip_decision["relevant_changes"],
        }

    # Check cache if enabled
    if use_cache:
        # Build input hash from JS-related files
        js_files = get_js_related_files(repo_root)
        if js_files:
            repo_path = Path(repo_root)
            js_file_paths = [
                repo_path / f for f in js_files if (repo_path / f).exists()
            ]
            input_hash = ft_cache.sha256_of_paths(js_file_paths)

            if ft_cache.is_tool_cache_valid(repo_root, "npm_test", input_hash):
                return {
                    "status": "ok",
                    "cached": True,
                    "reason": "NPM test results cached - no JS/TS changes detected",
                    "js_files_changed": skip_decision["js_files_changed"],
                    "relevant_changes": skip_decision["relevant_changes"],
                }

    # Run npm tests
    cmd = get_npm_test_command(repo_root)

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        duration = time.time() - start_time
        success = result.returncode == 0

        # Cache successful results
        if use_cache and success and js_files:
            repo_path = Path(repo_root)
            js_file_paths = [
                repo_path / f for f in js_files if (repo_path / f).exists()
            ]
            input_hash = ft_cache.sha256_of_paths(js_file_paths)

            ft_cache.write_tool_cache(
                repo_root,
                "npm_test",
                input_hash,
                "ok",
                {
                    "duration": duration,
                    "js_files_count": len(js_files),
                    "package_manager": detect_js_project_type(repo_root)[
                        "package_manager"
                    ],
                },
            )

        return {
            "status": "ok" if success else "fail",
            "exit_code": result.returncode,
            "duration": duration,
            "output": result.stdout + result.stderr,
            "command": cmd,
            "js_files_changed": skip_decision["js_files_changed"],
            "relevant_changes": skip_decision["relevant_changes"],
            "reason": skip_decision["reason"],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "duration": 120,
            "output": "NPM tests timed out after 120 seconds",
            "command": cmd,
            "js_files_changed": skip_decision["js_files_changed"],
            "relevant_changes": skip_decision["relevant_changes"],
        }
    except Exception as e:
        return {
            "status": "error",
            "duration": time.time() - start_time,
            "error": str(e),
            "output": f"Error running npm tests: {e}",
            "command": cmd,
            "js_files_changed": skip_decision["js_files_changed"],
            "relevant_changes": skip_decision["relevant_changes"],
        }


def analyze_npm_project(repo_root: str) -> Dict[str, Any]:
    """Comprehensive analysis of NPM project for optimization insights"""

    project_info = detect_js_project_type(repo_root)
    js_files = get_js_related_files(repo_root)

    # Estimate test complexity
    test_complexity = "unknown"
    estimated_duration = "unknown"

    if project_info["test_frameworks"]:
        if (
            "cypress" in project_info["test_frameworks"]
            or "playwright" in project_info["test_frameworks"]
        ):
            test_complexity = "high"  # E2E tests
            estimated_duration = "60-180s"
        elif (
            "jest" in project_info["test_frameworks"]
            or "vitest" in project_info["test_frameworks"]
        ):
            test_complexity = "medium"  # Unit tests
            estimated_duration = "10-60s"
        else:
            test_complexity = "low"
            estimated_duration = "5-30s"

    return {
        "project_info": project_info,
        "js_files_count": len(js_files),
        "js_files_sample": sorted(list(js_files))[:10],
        "test_complexity": test_complexity,
        "estimated_duration": estimated_duration,
        "optimization_potential": {
            "skip_on_no_js_changes": True,
            "cache_by_js_files": True,
            "package_manager_optimization": project_info["package_manager"] != "npm",
        },
    }
