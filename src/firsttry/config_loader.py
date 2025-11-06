from __future__ import annotations

# src/firsttry/config_loader.py
from pathlib import Path
from typing import Any

try:
    import tomllib  # py311+
except Exception:
    try:
        import tomli as tomllib  # type: ignore
    except Exception:
        tomllib = None  # type: ignore


def load_config() -> dict[str, Any]:
    """Load team / user config from:
    1. ./firsttry.toml
    2. ./pyproject.toml [tool.firsttry]
    """
    root = Path().resolve()

    ft = root / "firsttry.toml"
    if ft.exists() and tomllib is not None:
        return tomllib.loads(ft.read_text())

    pp = root / "pyproject.toml"
    if pp.exists() and tomllib is not None:
        data = tomllib.loads(pp.read_text())
        tool = data.get("tool") or {}
        ft_conf = tool.get("firsttry")
        if isinstance(ft_conf, dict):
            return ft_conf

    return {}


def plan_from_config(config: dict[str, Any]) -> list[dict[str, Any]] | None:
    """If the user/team provided an explicit plan, we build it from here.

    Supported:
    [tool.firsttry.run]
    tools = ["ruff", "mypy", "pytest", "bandit", "ci-parity"]

    [[tool.firsttry.custom]]
    name = "grep-todo"
    cmd = "grep -R 'TODO(admin)' src/"
    family = "custom"
    """
    if not config:
        return None

    tool_section = config.get("tool") or {}
    ft_section = tool_section.get("firsttry") or {}
    run = config.get("run") or ft_section.get("run") or {}
    tools = run.get("tools")

    customs = ft_section.get("custom") or config.get("custom") or []

    has_explicit_tools = bool(tools)
    has_customs = bool(customs)

    if not has_explicit_tools and not has_customs:
        return None

    plan: list[dict[str, Any]] = []

    if tools:
        for t in tools:
            # we don't know the family yet, call it t
            plan.append({"family": t, "tool": t})

    if customs:
        for c in customs:
            if not isinstance(c, dict):
                continue
            name = c.get("name") or c.get("tool") or "custom"
            cmd = c.get("cmd")
            if not cmd:
                continue
            family = c.get("family") or "custom"
            plan.append(
                {
                    "family": family,
                    "tool": name,
                    "cmd": cmd,
                },
            )

    return plan


def apply_overrides_to_plan(
    plan: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """After we have a base plan (from config OR from detection),
    we apply per-tool overrides.

    [tool.firsttry.tool.ruff]
    cmd = "ruff . --format=json --select=F,E"
    workers = 2
    """
    if not config:
        return plan

    tool_section = config.get("tool") or {}
    ft_section = tool_section.get("firsttry") or {}
    tool_cfgs = ft_section.get("tool") or {}

    new_plan: list[dict[str, Any]] = []
    for item in plan:
        tool = item.get("tool")
        override = tool_cfgs.get(tool)
        if override:
            merged = {**item, **override}
            new_plan.append(merged)
        else:
            new_plan.append(item)
    return new_plan


def apply_config_to_plan(
    plan: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Enrich auto-plan with user/team config.
    - Filter tools (if run.tools provided)
    - Override tool cmd / workers (if tool.* provided)
    - Add custom checks (if custom provided)
    """
    if not config:
        return plan

    run_section = config.get("run") or {}
    wanted_tools = run_section.get("tools")

    tool_overrides = (config.get("tool") or {}).get("firsttry", {})  # backward compat
    # better structure:
    # [tool.firsttry.tool.XYZ]
    tool_section = config.get("tool") or {}
    ft_tool_section = tool_section.get("firsttry") or {}
    tool_configs = ft_tool_section.get("tool") or {}

    # 1) filter
    if wanted_tools:
        wanted_set = set(wanted_tools)
        plan = [p for p in plan if p.get("tool") in wanted_set or p.get("family") in wanted_set]

    # 2) per-tool overrides
    new_plan: list[dict[str, Any]] = []
    for item in plan:
        tool = item.get("tool")
        override = tool_configs.get(tool) or tool_overrides.get(tool)
        if override:
            item = {**item, **override}
        new_plan.append(item)

    # 3) custom
    customs = ft_tool_section.get("custom") or config.get("custom") or []
    # can be list of tables
    for c in customs:
        if not isinstance(c, dict):
            continue
        name = c.get("name") or c.get("tool") or "custom"
        cmd = c.get("cmd")
        if not cmd:
            continue
        family = c.get("family") or "custom"
        new_plan.append(
            {
                "family": family,
                "tool": name,
                "cmd": cmd,
            },
        )

    return new_plan
