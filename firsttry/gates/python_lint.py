from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Gate, GateResult


class PythonRuffGate(Gate):
    gate_id = "python:ruff"
    patterns = ("*.py",)

    def run(self, root: Path) -> GateResult:
        try:
            proc = subprocess.run(
                ["ruff", "check", "."],
                cwd=str(root),
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="ruff not installed",
            )

        ok = proc.returncode == 0
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=(proc.stdout or "") + (proc.stderr or ""),
            watched_files=["pyproject.toml", "ruff.toml", ".ruff.toml"],
        )
