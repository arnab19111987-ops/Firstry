# src/firsttry/agents/ci/validation_parity.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ...agents.base import Agent, AgentResult
from ...ci_parser import resolve_ci_plan


@dataclass
class ValidationParityAgent(Agent):
    name: str = "ci_validation_parity"

    async def run(self, ctx: Any) -> AgentResult:
        repo_root = ctx.get("repo_root", ".")
        ci_plan = ctx.get("ci_plan")
        if ci_plan is None:
            ci_plan = resolve_ci_plan(repo_root) or []

        # --- CRITICAL FIX: no CI ≠ 100% parity ---
        if not ci_plan:
            return AgentResult(
                name=self.name,
                ok=True,  # not an error, just nothing to check
                duration_ms=5,
                issues=["No CI/CD files found to check for parity."],
                extra={
                    "score": None,
                    "reason": "no_ci_files_found",
                    "ci_plan": [],
                    "local_tools": ctx.get("local_tools", []),
                    "local_cmds": ctx.get("local_cmds", {}),
                },
            )
        # --- END FIX ---

        # local side
        local_tools = set(ctx.get("local_tools", []))
        local_cmds: Dict[str, str] = ctx.get("local_cmds") or {}

        missing_tools: List[str] = []
        cmd_mismatch: List[str] = []

        for item in ci_plan:
            ci_tool = item["tool"]
            ci_cmd = item["cmd"]

            # tool not in local plan
            if ci_tool not in local_tools:
                missing_tools.append(ci_tool)
                continue

            # tool present — check command-level parity
            local_cmd = local_cmds.get(ci_tool)
            if local_cmd and local_cmd.strip() != ci_cmd.strip():
                cmd_mismatch.append(f"{ci_tool}: CI='{ci_cmd}' local='{local_cmd}'")

        total = len(ci_plan)
        ok_count = total - len(missing_tools) - len(cmd_mismatch)
        score = ok_count / total if total else 0.0  # guarded anyway

        issues: List[str] = []
        if missing_tools:
            issues.append("missing CI tools: " + ", ".join(sorted(missing_tools)))
        if cmd_mismatch:
            issues.append("command drift: " + "; ".join(cmd_mismatch))

        return AgentResult(
            name=self.name,
            ok=score >= 0.85 and not missing_tools and not cmd_mismatch,
            duration_ms=15,
            issues=issues,
            extra={
                "ci_plan": ci_plan,
                "local_tools": sorted(local_tools),
                "local_cmds": local_cmds,
                "score": score,
            },
        )
