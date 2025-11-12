# src/firsttry/agents/ci/env_parity.py
from __future__ import annotations

import platform
from typing import Any

from ...agents.base import Agent
from ...agents.base import AgentResult
from ...ci_parser import detect_ci_runtime


class EnvParityAgent(Agent):
    name = "ci_env_parity"

    async def run(self, ctx: Any) -> AgentResult:
        repo_root = ctx.get("repo_root", ".")
        ci_env = detect_ci_runtime(repo_root)

        local_py = platform.python_version()
        local_os = platform.system().lower()

        issues = []
        score = 1.0

        if ci_env.get("python") and ci_env["python"] != local_py:
            issues.append(f"Python drift: CI={ci_env['python']} local={local_py}")
            score -= 0.25

        if ci_env.get("os") and ci_env["os"] != local_os:
            issues.append(f"OS drift: CI={ci_env['os']} local={local_os}")
            score -= 0.15

        return AgentResult(
            name=self.name,
            ok=score >= 0.75,
            duration_ms=5,
            issues=issues,
            extra={
                "ci_env": ci_env,
                "local_python": local_py,
                "local_os": local_os,
                "score": max(score, 0.0),
            },
        )
