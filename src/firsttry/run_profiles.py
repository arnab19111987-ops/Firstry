from __future__ import annotations
from typing import List

# if you want to fetch "all checks" for full/strict
try:
    from .check_registry import all_checks
except ImportError:
    def all_checks() -> list[str]:
        # fallback if check_registry not present yet
        return ["ruff", "repo_sanity", "black_check", "mypy", "pytest", "npm_test", "ci_parity"]


def select_checks(profile: str, changed: list[str] | None = None) -> List[str]:
    """
    Map CLI profile to the actual checks we want to run.
    Profiles:
      - fast  -> only quick, non-mutating, sub-5s
      - dev   -> what a solo dev can run often
      - full  -> everything we know
      - strict -> alias for full
    """
    changed = changed or []

    if profile == "fast":
        # this is what you can safely run on every commit
        return ["ruff", "repo_sanity"]

    if profile == "dev":
        # THIS is the fix: do not try to be "clever" yet.
        # run format + full mypy so people trust the tool.
        return ["ruff", "repo_sanity", "black_check", "mypy"]

    if profile in ("full", "strict"):
        return all_checks()

    # default/fallback
    return ["ruff", "repo_sanity"]


def get_pytest_mode_for_profile(profile: str) -> str:
    """Get the pytest mode for a given profile"""
    mode_map = {
        "fast": "smoke",     # Fast smoke tests only
        "dev": "smart",      # Smart failed-first + changed targeting  
        "full": "full",      # Full test suite with auto-parallel
        "strict": "full"     # Full test suite with auto-parallel
    }
    return mode_map.get(profile, "smart")


def should_use_parallel_pytest(profile: str, test_count: int = 0) -> bool:
    """Determine if parallel pytest should be used based on profile and test count"""
    if profile in ["full", "strict"]:
        return test_count > 200  # Use parallel for large suites
    return False  # Dev and fast profiles use smart targeting, not parallel chunks


def get_profile_description(profile: str) -> str:
    """Get human-readable description of a run profile"""
    descriptions = {
        "fast": "Quick static analysis only (ruff, sanity checks)",
        "dev": "Development workflow (linting + formatting + types)",
        "full": "Complete validation (all checks, no optimizations)", 
        "strict": "Full CI-equivalent validation",
    }
    return descriptions.get(profile, "Standard development checks")