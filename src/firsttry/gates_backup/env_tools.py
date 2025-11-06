from __future__ import annotations

import shutil
from pathlib import Path

from .base import Gate
from .base import GateResult

REQUIRED_TOOLS = [
    ("python:ruff", "ruff"),
    ("python:mypy", "mypy"),
    ("python:pytest", "pytest"),
    ("security:bandit", "bandit"),
    ("precommit:all", "pre-commit"),
]


class EnvToolsGate(Gate):
    """Check that the tools our other gates expect are actually installed in PATH.
    This prevents 'passed because tool missing' situations.
    """

    gate_id = "env:tools"
    patterns: tuple[str, ...] = ()

    def run(self, root: Path) -> GateResult:
        missing: list[str] = []
        for gate_name, bin_name in REQUIRED_TOOLS:
            if shutil.which(bin_name) is None:
                missing.append(f"{gate_name} → `{bin_name}` not found in PATH")

        if missing:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                output="Missing tools:\n" + "\n".join(missing),
            )

        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            output="All expected tools present in PATH.",
        )
