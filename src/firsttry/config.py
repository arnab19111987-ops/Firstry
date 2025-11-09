from __future__ import annotations

import warnings
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

try:
    import tomllib  # 3.11+
except Exception:  # py<3.11
    import tomli as tomllib  # type: ignore


@dataclass
class Timeouts:
    default: int = 300
    per_check: dict[str, int] = field(default_factory=dict)


@dataclass
class Workflow:
    pytest_depends_on: list[str] = field(default_factory=list)
    npm_test_depends_on: list[str] = field(default_factory=list)


@dataclass
class Config:
    tier: str = "lite"
    remote_cache: bool = False
    workers: int = 8
    timeouts: Timeouts = field(default_factory=Timeouts)
    checks_flags: dict[str, list[str]] = field(default_factory=dict)
    # workflow section (pytest/npm dependencies)
    workflow: Workflow = field(default_factory=Workflow)


def load_config(repo_root: Path) -> Config:
    path = repo_root / "firsttry.toml"
    if not path.exists():
        return Config()

    data = tomllib.loads(path.read_text())
    core = data.get("core", {})
    c = Config(
        tier=core.get("tier", "lite"),
        remote_cache=bool(core.get("remote_cache", False)),
        workers=int(core.get("workers", 8)),
    )
    to = data.get("timeouts", {})
    c.timeouts.default = int(to.get("default", 300))
    c.timeouts.per_check = (
        {k: int(v) for k, v in to.get("per_check", {}).items()}
        if isinstance(to.get("per_check", {}), dict)
        else {}
    )
    # checks.flags table may be dotted in some toml variants
    c.checks_flags = (
        {k: list(v) for k, v in data.get("checks.flags", {}).items()}
        if "checks.flags" in data
        else {}
    )
    # workflow parsing
    wf = data.get("workflow", {}) or {}
    c.workflow = Workflow(
        pytest_depends_on=list(wf.get("pytest_depends_on", [])),
        npm_test_depends_on=list(wf.get("npm-test_depends_on", []))
        or list(wf.get("npm_test_depends_on", [])),
    )
    return c


def timeout_for(cfg: Config, check_id: str) -> int:
    return int(cfg.timeouts.per_check.get(check_id, cfg.timeouts.default))


def workflow_requires(cfg: Config) -> list[str]:
    # unified list the planner understands per language section
    return list(set(cfg.workflow.pytest_depends_on + cfg.workflow.npm_test_depends_on))


# Temporary compatibility alias
# Historically some tooling (under `tools/firsttry`) exported a
# `FirstTryConfig` symbol. When tests or scripts accidentally import the
# repository `src` package rather than the tooling package this caused an
# ImportError during collection. Keep a small alias here so those imports
# succeed while the tooling package is migrated/renamed.
#
# NOTE: This is a temporary shim. Remove after renaming the tooling package
# (e.g. to `firsttry_tools`).
FirstTryConfig = Config  # TEMP compat; remove after tooling package rename
warnings.warn(
    "firsttry.config.FirstTryConfig is deprecated; import Config instead. "
    "This alias will be removed after the tooling package is renamed.",
    DeprecationWarning,
    stacklevel=2,
)

# Explicit export surface. Keep alias on the export list while it's present.
__all__ = ["Config", "FirstTryConfig"]  # TEMP: remove alias on T2
