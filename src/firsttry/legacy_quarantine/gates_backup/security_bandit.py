from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Gate, GateResult


class SecurityBanditGate(Gate):
    gate_id = "security:bandit"
    patterns = ("*.py",)

    def run(self, root: Path) -> GateResult:
        try:
            proc = subprocess.run(
                ["bandit", "-r", "."],
                cwd=str(root),
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="bandit not installed",
            )

        ok = proc.returncode == 0
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=(proc.stdout or "") + (proc.stderr or ""),
        )
