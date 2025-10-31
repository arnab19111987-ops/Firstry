from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Gate, GateResult


class PythonPytestGate(Gate):
    gate_id = "python:pytest"
    # reacts to tests/ and test_*
    patterns = ("tests/", "test_", "*.py")

    def run(self, root: Path) -> GateResult:
        try:
            proc = subprocess.run(
                ["pytest", "-q"],
                cwd=str(root),
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="pytest not installed",
            )

        ok = proc.returncode == 0
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=(proc.stdout or "") + (proc.stderr or ""),
            watched_files=["pytest.ini", "pyproject.toml", "tests/"],
        )
