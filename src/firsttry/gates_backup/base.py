from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class GateResult:
    gate_id: str
    ok: bool
    output: str = ""
    skipped: bool = False
    reason: str = ""
    watched_files: List[str] | None = None


class Gate:
    gate_id: str = "base"
    # which patterns this gate is interested in
    patterns: Sequence[str] = ("*.py",)

    def should_run_for(self, changed_files: list[str]) -> bool:
        if not changed_files:
            # full run
            return True
        # naive matcher — fine for now
        for f in changed_files:
            for p in self.patterns:
                if p.startswith("*.") and f.endswith(p[1:]):  # "*.py" → ".py"
                    return True
                if p.endswith("/") and f.startswith(p):
                    return True
        return False

    def run(self, root):
        raise NotImplementedError
