from __future__ import annotations

from pathlib import Path

from .base import Gate
from .base import GateResult


class DriftCheckGate(Gate):
    """PHASE 2 placeholder.
    Later:
      - compare DB migrations vs models
      - compare requirements.txt vs lock
      - compare generated client vs spec
    """

    gate_id = "drift:check"
    patterns = (
        "alembic/",
        "migrations/",
        "requirements.txt",
        "pyproject.toml",
    )

    def run(self, root: Path) -> GateResult:
        msg = (
            "Drift check (placeholder):\n"
            "- TODO: check alembic heads\n"
            "- TODO: check requirements vs lock\n"
        )
        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            output=msg,
            watched_files=[
                "alembic/",
                "migrations/",
                "requirements.txt",
                "pyproject.toml",
            ],
        )
