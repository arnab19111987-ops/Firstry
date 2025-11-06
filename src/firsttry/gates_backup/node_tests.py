from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Gate
from .base import GateResult


class NodeNpmTestGate(Gate):
    gate_id = "node:npm"
    patterns = ("package.json",)

    def run(self, root: Path) -> GateResult:
        try:
            proc = subprocess.run(
                ["npm", "test"],
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
                reason="npm not installed",
            )

        ok = proc.returncode == 0
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=(proc.stdout or "") + (proc.stderr or ""),
            watched_files=["package.json", "package-lock.json", "pnpm-lock.yaml"],
        )
