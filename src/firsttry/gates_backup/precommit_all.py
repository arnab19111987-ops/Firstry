from __future__ import annotations

import subprocess
from pathlib import Path

from .base import Gate
from .base import GateResult


class PreCommitAllGate(Gate):
    gate_id = "precommit:all"
    patterns = (".pre-commit-config.yaml",)

    def run(self, root: Path) -> GateResult:
        cfg = root / ".pre-commit-config.yaml"
        if not cfg.exists():
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="no .pre-commit-config.yaml",
            )

        try:
            proc = subprocess.run(
                ["pre-commit", "run", "--all-files"],
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
                reason="pre-commit not installed",
            )

        ok = proc.returncode == 0
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=(proc.stdout or "") + (proc.stderr or ""),
            watched_files=[".pre-commit-config.yaml"],
        )
