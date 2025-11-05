# src/firsttry/sync.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import tomllib  # py311+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

from .ci_parser import resolve_ci_plan


CONFIG_PATH = Path("firsttry.toml")


def _load_existing() -> Dict[str, Any]:
    """
    Load firsttry.toml if present.
    We intentionally do NOT try to update pyproject.toml
    to avoid destroying a user's big file.
    """
    if CONFIG_PATH.exists() and tomllib is not None:
        return tomllib.loads(CONFIG_PATH.read_text())
    return {}


def _ensure_nested(d: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    cur = d
    for k in keys:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    return cur


def _toml_dump_firsttry(data: Dict[str, Any]) -> str:
    """
    Very small TOML writer just for our structure:

    [tool.firsttry]
    fail_on_drift = true

    [tool.firsttry.run]
    tools = ["ruff", "pytest", "ci-parity"]

    [tool.firsttry.tool.pytest]
    cmd = "pytest -m 'not slow'"
    """
    lines: List[str] = []

    tool = data.get("tool", {})
    ft = tool.get("firsttry", {})

    # [tool.firsttry]
    lines.append("[tool.firsttry]")
    for k, v in ft.items():
        if k in ("run", "tool"):
            continue
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
    lines.append("")

    # [tool.firsttry.run]
    run = ft.get("run", {})
    lines.append("[tool.firsttry.run]")
    tools = run.get("tools", [])
    if tools:
        # write array
        arr = ", ".join(f'"{t}"' for t in tools)
        lines.append(f"tools = [{arr}]")
    else:
        lines.append("tools = []")
    lines.append("")

    # [tool.firsttry.tool.<name>]
    tool_cfgs = ft.get("tool", {})
    for name, cfg in tool_cfgs.items():
        # Quote tool names that contain spaces or special characters
        if " " in name or "-" in name or not name.isidentifier():
            lines.append(f'[tool.firsttry.tool."{name}"]')
        else:
            lines.append(f"[tool.firsttry.tool.{name}]")
        for ck, cv in cfg.items():
            if isinstance(cv, bool):
                lines.append(f"{ck} = {str(cv).lower()}")
            elif isinstance(cv, (int, float)):
                lines.append(f"{ck} = {cv}")
            else:
                lines.append(f'{ck} = "{cv}"')
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def sync_with_ci(repo_root: str = ".") -> Tuple[bool, str]:
    """
    1. resolve CI plan
    2. load current firsttry.toml (if any)
    3. merge CI into config:
       - add CI tools to run.tools (if missing)
       - for each CI tool, set [tool.firsttry.tool.<tool>].cmd to CI cmd
       - ensure ci-parity is present
       - set fail_on_drift = true
    4. write firsttry.toml
    """
    ci_plan = resolve_ci_plan(repo_root)
    if not ci_plan:
        return False, "No CI/CD files found — nothing to sync."

    existing = _load_existing()

    # ensure nested structure
    tool = _ensure_nested(existing, "tool")
    ft = _ensure_nested(tool, "firsttry")
    run = _ensure_nested(ft, "run")
    tool_cfgs = _ensure_nested(ft, "tool")

    # existing run tools
    current_tools = set(run.get("tools", []))

    added = 0
    updated = 0

    # pull in CI tools
    for item in ci_plan:
        t = item["tool"]
        cmd = item["cmd"]
        current_tools.add(t)
        # write per-tool cmd
        cur_tool_cfg = tool_cfgs.get(t) or {}
        if cur_tool_cfg.get("cmd") != cmd:
            cur_tool_cfg["cmd"] = cmd
            tool_cfgs[t] = cur_tool_cfg
            updated += 1

    # always add ci-parity to run list
    if "ci-parity" not in current_tools:
        current_tools.add("ci-parity")
        added += 1

    # update run.tools
    run["tools"] = sorted(current_tools)

    # enforce drift in synced config
    ft["fail_on_drift"] = True

    # finalize back
    tool["firsttry"] = ft
    existing["tool"] = tool

    # write file
    out = _toml_dump_firsttry(existing)
    CONFIG_PATH.write_text(out, encoding="utf-8")

    msg_bits = []
    msg_bits.append(f"Synced {len(ci_plan)} CI entries into firsttry.toml.")
    if updated:
        msg_bits.append(f"Updated {updated} tool commands.")
    if added:
        msg_bits.append(f"Added {added} missing tools.")
    msg_bits.append("Enabled fail_on_drift = true.")
    return True, " ".join(msg_bits)
