from __future__ import annotations

from pathlib import Path
from typing import List, Callable, Any, Dict

from .tools.ruff_tool import RuffTool
from .tools.mypy_tool import MypyTool
from .tools.pytest_tool import PytestTool
from .tools.npm_test_tool import NpmTestTool


ToolFactory = Callable[[Path], Any]


class RunProfile:
    def __init__(
        self,
        name: str,
        fast_tools: List[ToolFactory],
        mutating_tools: List[ToolFactory] | None = None,
        slow_tools: List[ToolFactory] | None = None,
    ):
        self.name = name
        self._fast_tools = fast_tools
        self._mutating_tools = mutating_tools or []
        self._slow_tools = slow_tools or []

    def fast(self, repo_root: Path):
        return [factory(repo_root) for factory in self._fast_tools]

    def mutating(self, repo_root: Path):
        return [factory(repo_root) for factory in self._mutating_tools]

    def slow(self, repo_root: Path):
        return [factory(repo_root) for factory in self._slow_tools]

    @property
    def has_mutating(self) -> bool:
        return bool(self._mutating_tools)

    @property
    def has_slow(self) -> bool:
        return bool(self._slow_tools)


def dev_profile() -> RunProfile:
    return RunProfile(
        name="dev",
        fast_tools=[lambda root: RuffTool(root),],
        mutating_tools=[
            # put black here if you have one
        ],
        slow_tools=[
            lambda root: MypyTool(root),
            lambda root: PytestTool(root),
        ],
    )


# Legacy compatibility function
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
        # Legacy fallback - provide comprehensive check list
        return ["ruff", "repo_sanity", "black_check", "mypy", "pytest", "npm_test", "ci_parity"]

    # default/fallback
    return ["ruff", "repo_sanity"]


# New 4-tier profile system
from .license_guard import get_tier

PROFILES_BY_TIER = {
    "free-lite": "dev_fast",
    "free-strict": "dev_strict", 
    "pro": "team_strict",
    "promax": "enterprise",
}


def get_profile_for_current_tier() -> str:
    tier = get_tier()
    return PROFILES_BY_TIER.get(tier, "dev_fast")


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