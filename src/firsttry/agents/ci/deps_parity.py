# src/firsttry/agents/ci/deps_parity.py
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from ...agents.base import Agent, AgentResult
from ...ci_parser import detect_ci_deps
from ...deps import read_local_deps


class DependencyParityAgent(Agent):
    name = "ci_dependency_parity"

    async def run(self, ctx: Any) -> AgentResult:
        repo_root = ctx.get("repo_root", ".")
        ci_deps: Dict[str, str] = detect_ci_deps(repo_root)
        local_deps: Dict[str, str] = read_local_deps(repo_root)

        # if CI only said "requirements.txt", we just check presence
        if ci_deps == {"requirements.txt": "*"}:
            if "requirements.txt" not in local_deps:
                return AgentResult(
                    name=self.name,
                    ok=False,
                    duration_ms=5,
                    issues=["requirements.txt is used in CI but not present locally"],
                    extra={"ci_deps": ci_deps, "local_deps": local_deps},
                )
            return AgentResult(
                name=self.name,
                ok=True,
                duration_ms=5,
                issues=[],
                extra={"ci_deps": ci_deps, "local_deps": local_deps},
            )

        missing: Set[str] = set(ci_deps) - set(local_deps)
        version_drift: List[Tuple[str, str, str]] = []
        for dep, ver in ci_deps.items():
            if dep in local_deps and local_deps[dep] != ver:
                version_drift.append((dep, ver, local_deps[dep]))

        total = max(1, len(ci_deps))
        ok_count = total - len(missing) - len(version_drift)
        score = ok_count / total

        issues = []
        if missing:
            issues.append("Missing deps locally: " + ", ".join(sorted(missing)))
        if version_drift:
            issues.append("Version drift: " + ", ".join(f"{dep} CI:{ci_ver} local:{local_ver}" for dep, ci_ver, local_ver in version_drift))

        return AgentResult(
            name=self.name,
            ok=score >= 0.8,
            duration_ms=10,
            issues=issues,
            extra={
                "ci_deps": ci_deps,
                "local_deps": local_deps,
                "version_drift": version_drift,
                "missing": sorted(missing),
                "score": score,
            },
        )