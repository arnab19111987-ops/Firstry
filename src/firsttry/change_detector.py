"""
Change detection for optimizing FirstTry runs.
Maps file changes to relevant checks to skip unnecessary work.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Set


def get_changed_files(repo_root: str = ".") -> List[str]:
    """
    Get list of changed files using git.
    Returns files changed since HEAD (uncommitted changes).
    Falls back to all files if git fails.
    """
    try:
        # Try to get unstaged changes
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")

        # Also check staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")

        # If no changes, return empty list
        return []

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        # If git fails, assume all files changed (run everything)
        return ["**"]


def categorize_changed_files(changed_files: List[str]) -> Dict[str, List[str]]:
    """
    Categorize changed files by type.
    """
    categories: Dict[str, List[str]] = {
        "python": [],
        "javascript": [],
        "docs": [],
        "config": [],
        "ci": [],
        "other": [],
    }

    for file_path in changed_files:
        if file_path == "**":
            # Special marker for "all files"
            categories["other"].append(file_path)
            continue

        path = Path(file_path)
        suffix = path.suffix.lower()
        name = path.name.lower()

        # Python files
        if suffix in {".py", ".pyi", ".pyx"}:
            categories["python"].append(file_path)

        # JavaScript/TypeScript files
        elif suffix in {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}:
            categories["javascript"].append(file_path)

        # Documentation files
        elif suffix in {".md", ".rst", ".txt"} or "doc" in str(path).lower():
            categories["docs"].append(file_path)

        # CI/CD files
        elif (
            ".github" in str(path)
            or name in {"tox.ini", "makefile", ".travis.yml", ".gitlab-ci.yml"}
            or name.startswith(".github")
        ):
            categories["ci"].append(file_path)

        # Config files
        elif name in {
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "firsttry.toml",
            ".firsttry.toml",
        }:
            categories["config"].append(file_path)

        else:
            categories["other"].append(file_path)

    return categories


def map_changes_to_checks(file_categories: Dict[str, List[str]]) -> Set[str]:
    """
    Map file changes to relevant check families.
    """
    relevant_checks = set()

    # If "all files" marker or other files changed, run everything
    if file_categories["other"] and any(f == "**" for f in file_categories["other"]):
        return {"*all*"}

    # Python changes → Python checks
    if file_categories["python"]:
        relevant_checks.update({"ruff", "mypy", "black", "pytest", "bandit", "pylint"})

    # JavaScript changes → JS checks
    if file_categories["javascript"]:
        relevant_checks.update({"npm", "eslint", "prettier"})

    # Config changes → potentially everything
    if file_categories["config"]:
        # Package config changes → run relevant language checks
        for config_file in file_categories["config"]:
            if "package.json" in config_file or "package-lock" in config_file:
                relevant_checks.update({"npm", "eslint"})
            if "pyproject.toml" in config_file or "requirements" in config_file:
                relevant_checks.update({"ruff", "mypy", "pytest", "bandit"})
            if "firsttry.toml" in config_file:
                relevant_checks.add("*all*")

    # CI changes → CI parity
    if file_categories["ci"]:
        relevant_checks.add("ci-parity")

    # Unknown/other changes → run everything as safety
    if file_categories["other"]:
        relevant_checks.add("*all*")

    # If only docs changed, skip most checks
    if file_categories["docs"] and not any(
        file_categories[k] for k in ["python", "javascript", "config", "ci", "other"]
    ):
        print("📖 Only documentation files changed - skipping checks")
        return set()  # Skip all checks

    return relevant_checks


def filter_plan_by_changes(
    plan: List[Dict], repo_root: str = ".", changed_only: bool = False
) -> List[Dict]:
    """
    Filter a plan to only include checks relevant to changed files.

    Args:
        plan: Original check plan
        repo_root: Repository root directory
        changed_only: Whether to enable change-based filtering

    Returns:
        Filtered plan with only relevant checks
    """
    if not changed_only:
        return plan

    # Get changed files
    changed_files = get_changed_files(repo_root)

    if not changed_files:
        print("📝 No changes detected - skipping all checks")
        return []

    # Categorize changes
    file_categories = categorize_changed_files(changed_files)

    # Map to relevant checks
    relevant_checks = map_changes_to_checks(file_categories)

    if "*all*" in relevant_checks:
        print("🔄 Major changes detected - running all checks")
        return plan

    if not relevant_checks:
        return []

    # Filter plan
    filtered_plan = []
    skipped_checks = []

    for item in plan:
        tool = item.get("tool") or item.get("family") or str(item)
        family = item.get("family") or tool

        # Check if this tool/family is relevant
        if any(
            check in tool.lower() or check in family.lower()
            for check in relevant_checks
        ):
            filtered_plan.append(item)
        else:
            skipped_checks.append(tool)

    # Show what was skipped
    if skipped_checks:
        print(f"⏭️  Skipped checks (no relevant changes): {', '.join(skipped_checks)}")

    if filtered_plan:
        relevant_tools = [item.get("tool") or str(item) for item in filtered_plan]
        print(f"🎯 Running relevant checks: {', '.join(relevant_tools)}")

    return filtered_plan
