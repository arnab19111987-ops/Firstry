from __future__ import annotations

from pathlib import Path

from .base import Gate
from .base import GateResult


class CiFilesChangedGate(Gate):
    """MVP CI-sensitivity gate.
    - If .github/workflows exists, list the workflow files.
    - Later you can teach this gate to compare mtimes or hashes and fail on change.
    """

    gate_id = "ci:files"
    patterns = (".github/workflows/", "tox.ini")

    def run(self, root: Path) -> GateResult:
        gh = root / ".github" / "workflows"
        lines: list[str] = []

        if gh.exists():
            wf = sorted(gh.rglob("*.yml"))
            if not wf:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    output="CI directory present but no *.yml workflows found.",
                    watched_files=[".github/workflows/"],
                )
            lines.append("CI workflows found:")
            for p in wf:
                rel = p.relative_to(root)
                lines.append(f"- {rel}")
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                output="\n".join(lines),
                watched_files=[".github/workflows/"],
            )

        tox = root / "tox.ini"
        if tox.exists():
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                output="tox.ini present (CI may run tox environments).",
                watched_files=["tox.ini"],
            )

        return GateResult(
            gate_id=self.gate_id,
            ok=True,
            output="No CI workflow directory detected.",
        )
