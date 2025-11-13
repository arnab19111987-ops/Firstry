# src/firsttry/runners/ci_parity.py
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..agents.ci.deps_parity import DependencyParityAgent
from ..agents.ci.env_parity import EnvParityAgent
from ..agents.ci.validation_parity import ValidationParityAgent
from ..ci_parser import resolve_ci_plan
from .base import CheckRunner, RunResult


class CiParityRunner(CheckRunner):
    check_id = "ci-parity"

    def run(
        self, repo_root: Path, files: list[str] | None = None, *, timeout_s: int | None = None
    ) -> RunResult:
        ctx: dict[str, Any] = {"repo_root": str(repo_root)}
        # make sure ctx has ci_plan
        if "ci_plan" not in ctx:
            ctx["ci_plan"] = resolve_ci_plan(ctx.get("repo_root", ".")) or []

        v = ValidationParityAgent()
        e = EnvParityAgent()
        d = DependencyParityAgent()

        # run async agents synchronously
        v_res = asyncio.run(v.run(ctx))
        e_res = asyncio.run(e.run(ctx))
        d_res = asyncio.run(d.run(ctx))

        ok = (
            getattr(v_res, "ok", False)
            and getattr(e_res, "ok", False)
            and getattr(d_res, "ok", False)
        )

        lines: list[str] = []
        for res in (v_res, e_res, d_res):
            for issue in getattr(res, "issues", []) or []:
                lines.append(f"{getattr(res, 'name', 'agent')}: {issue}")
        msg = "\n".join(lines) if lines else "ci parity ok"

        extra: dict[str, Any] = {
            "validation": getattr(v_res, "extra", None),
            "env": getattr(e_res, "extra", None),
            "deps": getattr(d_res, "extra", None),
        }

        return RunResult(
            name="ci-parity",
            rc=0 if ok else 1,
            stdout="",
            stderr="",
            duration_ms=0,
            ok=ok,
            message=msg,
            extra=extra,
            tool="ci-parity",
        )
