# src/firsttry/runners/ci_parity.py
from __future__ import annotations

from typing import Any, Dict

from ..agents.ci.deps_parity import DependencyParityAgent
from ..agents.ci.env_parity import EnvParityAgent
from ..agents.ci.validation_parity import ValidationParityAgent
from ..ci_parser import resolve_ci_plan
from .base import BaseRunner, RunnerResult


class CiParityRunner(BaseRunner):
    tool = "ci-parity"

    async def run(
        self, idx: int, ctx: Dict[str, Any], item: Dict[str, Any]
    ) -> RunnerResult:
        # make sure ctx has ci_plan
        if "ci_plan" not in ctx:
            ctx["ci_plan"] = resolve_ci_plan(ctx.get("repo_root", ".")) or []

        v = ValidationParityAgent()
        e = EnvParityAgent()
        d = DependencyParityAgent()

        v_res, e_res, d_res = await v.run(ctx), await e.run(ctx), await d.run(ctx)

        ok = v_res.ok and e_res.ok and d_res.ok

        lines = []
        for res in (v_res, e_res, d_res):
            for issue in res.issues:
                lines.append(f"{res.name}: {issue}")
        msg = "\n".join(lines) if lines else "ci parity ok"

        return RunnerResult(
            name="ci-parity",
            ok=ok,
            message=msg,
            tool="ci-parity",
            extra={
                "validation": v_res.extra,
                "env": e_res.extra,
                "deps": d_res.extra,
            },
        )
