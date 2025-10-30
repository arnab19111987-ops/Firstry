from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .base import Gate, GateResult


class CoverageCheckGate(Gate):
    gate_id = "coverage:check"
    patterns = ("coverage.xml",)

    def __init__(self, threshold: int = 80):
        self.threshold = threshold

    def run(self, root: Path) -> GateResult:
        cov_file = root / "coverage.xml"
        if not cov_file.exists():
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                output="coverage.xml missing. Run tests with coverage first.",
                watched_files=["coverage.xml"],
            )
        try:
            tree = ET.parse(str(cov_file))
            root_el = tree.getroot()
            line_rate_str = root_el.attrib.get("line-rate")
            if line_rate_str is None:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=False,
                    output="coverage.xml present but missing 'line-rate' attribute.",
                    watched_files=["coverage.xml"],
                )
            line_rate = float(line_rate_str) * 100.0
        except (ET.ParseError, ValueError) as exc:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                output=f"failed to parse coverage.xml (invalid XML or number): {exc}",
                watched_files=["coverage.xml"],
            )
        except Exception as exc:  # safety net
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                output=f"unexpected error while reading coverage.xml: {exc}",
                watched_files=["coverage.xml"],
            )

        ok = line_rate >= self.threshold
        return GateResult(
            gate_id=self.gate_id,
            ok=ok,
            output=f"coverage: {line_rate:.2f}% (required: {self.threshold}%)",
            watched_files=["coverage.xml"],
        )
